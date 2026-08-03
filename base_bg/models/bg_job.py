##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
import random
from datetime import timedelta

import psycopg2
from markupsafe import Markup
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

_logger = logging.getLogger(__name__)

# Number of times a worker retries acquiring the next job when it loses the race
# against a concurrent worker (SerializationFailure). Retrying in-process absorbs the
# transient contention instead of surrendering and rescheduling every cron at once
# (trigger storm). Mirrors saas_provider.saas_database._acquire_next_task.
MAX_ACQUIRE_RETRIES = 5


class BgJob(models.Model):
    _name = "bg.job"
    _description = "Background Job"
    _order = "priority, create_date desc"

    name = fields.Char(
        string="Job Name",
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("enqueued", "Enqueued"),
            ("waiting", "Waiting For Previous Job"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("canceled", "Canceled"),
        ],
        default="enqueued",
        required=True,
        help="Current state of the job",
    )
    model = fields.Char(
        required=True,
        readonly=True,
        help="The model name on which the job method will be executed",
    )
    method = fields.Char(
        required=True,
        readonly=True,
        help="The method name to be executed",
    )
    args_json = fields.Json(
        readonly=True,
        help="Positional arguments for the method call, serialized as JSON",
    )
    kwargs_json = fields.Json(
        readonly=True,
        help="Keyword arguments for the method call, serialized as JSON",
    )
    context_json = fields.Json(
        readonly=True,
        help="Context to be used when executing the job, serialized as JSON",
    )
    priority = fields.Integer(
        default=10,
        readonly=True,
        help="Job priority (lower number means higher priority)",
    )
    max_retries = fields.Integer(
        default=3,
        readonly=True,
        help="Maximum number of retry attempts",
    )
    retry_count = fields.Integer(
        default=0,
        readonly=True,
        help="Total number of attempts made so far (transient + non-transient).",
    )
    transient_retry_count = fields.Integer(
        default=0,
        readonly=True,
        help="Number of attempts lost to transient PostgreSQL contention (serialization / "
        "deadlock / lock timeout); kept separate so a contention spike does not consume the "
        "normal retry budget.",
    )
    start_time = fields.Datetime(
        readonly=True,
        help="When the job execution started",
    )
    end_time = fields.Datetime(
        readonly=True,
        help="When the job execution finished",
    )
    cancel_time = fields.Datetime(
        readonly=True,
        help="When the job was canceled",
    )
    duration = fields.Float(
        compute="_compute_duration",
        store=True,
        help="Job execution duration in seconds",
    )
    error_message = fields.Text(
        readonly=True,
        help="Error message from the last failed execution",
    )
    batch_key = fields.Char(
        required=True,
        readonly=True,
        index=True,
        help="Identifier for related jobs in a batch",
    )
    next_job_id = fields.Many2one(
        "bg.job",
        readonly=True,
        help="Next job in the batch sequence",
    )
    next_retry_at = fields.Datetime(
        readonly=True,
        help="Earliest moment this job may be picked up again after a transient (e.g. serialization) failure.",
    )

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for job in self:
            if job.start_time and job.end_time:
                delta = job.end_time - job.start_time
                job.duration = delta.total_seconds()
            else:
                job.duration = 0.0

    def action_cancel(self):
        """
        Action to manually cancel enqueued jobs
        """
        self.ensure_one()
        if self.state != "enqueued":
            raise UserError(_("Only enqueued jobs can be canceled"))

        (self | self._get_next_jobs()).cancel()

    def action_retry(self):
        """
        Action to manually retry failed job
        """
        self.ensure_one()
        if self.state != "failed":
            raise UserError(_("Only failed jobs can be retried"))

        self.enqueue(retry=True)
        self._get_next_jobs().wait()

    def action_open_records(self) -> dict:
        """
        Action to open the records related to the job
        """
        self.ensure_one()
        records = self._get_records()
        return {
            "name": _("Related Records"),
            "type": "ir.actions.act_window",
            "res_model": self.model,
            "view_mode": "list,form",
            "domain": [("id", "in", records.ids)],
        }

    def action_open_batch_jobs(self) -> dict:
        """
        Action to open all jobs in the same batch
        """
        self.ensure_one()
        return {
            "name": _("Batch Jobs: %s", self.batch_key[:8]),
            "type": "ir.actions.act_window",
            "res_model": "bg.job",
            "view_mode": "list,form",
            "domain": [("batch_key", "=", self.batch_key)],
        }

    def run(self):
        """
        Executes the job.

        The method runs inside this transaction and is retried on transient
        failures (see ``_handle_job_error``), so it may execute more than once
        (at-least-once semantics). Job methods with non-transactional side effects
        (emails, external API calls) should be idempotent or guard against repeats.
        """
        self.ensure_one()
        if self.state != "running":
            raise UserError(_("Only running jobs can be executed"))

        self.env.cr.commit()  # pylint: disable=invalid-commit
        try:
            context = dict(self.context_json or {})
            context.update({"bg_job": True, "bg_job_id": self.id})

            # Extract record IDs if present in kwargs or args
            args = list(self.args_json or [])
            kwargs = dict(self.kwargs_json or {})
            kwargs.pop("_record_ids")  # Remove _record_ids from kwargs if present
            records = self._get_records().with_context(**context).with_user(self.create_uid)

            # Execute the method and capture the result
            result = getattr(records, self.method)(*args, **kwargs)
            self.finish()
            if result:
                self._notify_user(result)

            self.env.cr.commit()  # pylint: disable=invalid-commit
        except Exception as e:
            self.env.cr.rollback()  # pylint: disable=invalid-commit
            self._handle_job_error(e)
            self.env.cr.commit()  # pylint: disable=invalid-commit

    def enqueue(self, retry: bool = False):
        """Mark the job as enqueued, clearing any pending backoff gate."""
        data: dict[str, str | int | bool] = {
            "state": "enqueued",
            "next_retry_at": False,
        }
        if retry:
            data.update(
                {
                    "retry_count": 0,
                    "transient_retry_count": 0,
                    "error_message": False,
                }
            )
        self.write(data)

    def finish(self):
        """
        Mark the job as done and set the end time.
        Also enqueue the next job in the batch if it exists.

        The cron is intentionally NOT triggered here: ``_cron_run_enqueued_jobs``
        already re-triggers itself while eligible jobs remain, so triggering on
        every single ``finish`` only piles redundant writes on ``ir_cron`` and
        fuels serialization contention on the scheduler under load.
        """
        self.write(
            {
                "state": "done",
                "end_time": fields.Datetime.now(),
            }
        )
        self.filtered("next_job_id").mapped("next_job_id").enqueue()

    def wait(self):
        """Mark the job as waiting for the previous job to complete."""
        self.write(
            {
                "state": "waiting",
            }
        )

    def fail(self, error_message: str, notify: bool = True):
        """Mark the job as failed with an error message."""
        self.write(
            {
                "state": "failed",
                "end_time": fields.Datetime.now(),
                "error_message": error_message,
                "next_retry_at": False,
            }
        )
        if notify:
            message = _("Job %s failed: %s") % (self.name, error_message)
            records = self._get_records().mapped(lambda r: r and r._get_html_link())
            if records:
                message += "<br/>" + _("Related records: %s") % (", ".join(records))
            self._notify_user(message)

    def cancel(self, message: str | None = None):
        """Cancel the jobs received."""
        self.write(
            {
                "state": "canceled",
                "cancel_time": fields.Datetime.now(),
                "error_message": message,
                "next_retry_at": False,
            }
        )

    def _get_records(self) -> models.BaseModel:
        """
        Helper method to retrieve the records related to the job based on the kwargs.

        :return: A recordset of the related records
        """
        kwargs = dict(self.kwargs_json or {})
        record_ids = kwargs.get("_record_ids", [])
        records = self.env[self.model].browse(record_ids)
        return records

    def _handle_job_error(self, error: Exception | str) -> bool:
        """
        Handle a job execution error and decide whether to retry.

        Transient PostgreSQL contention (serialization failure, deadlock, lock
        timeout) raised while *running* the job is expected under concurrency and
        clears on its own once the contending transactions drain. Such errors are
        retried with exponential backoff + jitter using their OWN budget
        (``transient_retry_count`` vs ``base_bg.transient_max_retries``), kept
        separate from the normal ``retry_count`` / ``max_retries`` budget so a
        contention spike never eats the retries meant for real errors. Every other
        error keeps the original immediate-retry-then-fail behavior.

        ``retry_count`` counts every attempt (transient + non-transient) so callers
        that display an attempt number stay accurate; the non-transient budget is
        measured on non-transient attempts only.

        (Concurrency failures while *acquiring* the job are handled earlier, in
        ``_cron_run_enqueued_jobs``, before any work is done.)

        :param error: The exception raised during job execution, or a message.
        :return: True if the job was re-enqueued for another attempt, False if it
            was failed permanently. Overrides rely on this to report retries.
        """
        error_msg = str(error)
        self.retry_count += 1
        if self._is_transient_error(error):
            self.transient_retry_count += 1
            if self.transient_retry_count < self._get_transient_max_retries():
                delay = self._compute_backoff_delay(self.transient_retry_count)
                next_retry_at = fields.Datetime.now() + timedelta(seconds=delay)
                self.write(
                    {
                        "state": "enqueued",
                        "next_retry_at": next_retry_at,
                        "error_message": error_msg,
                    }
                )
                # Wake a runner exactly when the backoff elapses: a backing-off job
                # is excluded from the self-retrigger, so without this it would idle
                # until the next periodic cron tick.
                self.env["base.bg"].sudo()._trigger_crons(at=next_retry_at)
                _logger.warning(
                    "Job %s hit transient contention, backing off %.1fs before retry #%d: %s",
                    self.name,
                    delay,
                    self.transient_retry_count,
                    error_msg,
                )
                return True
            _logger.error(
                "Job %s failed permanently after %d transient retries: %s",
                self.name,
                self.transient_retry_count,
                error_msg,
            )
            return self._give_up(error_msg)

        # Non-transient error: budget measured on non-transient attempts only.
        non_transient_attempts = self.retry_count - self.transient_retry_count
        if non_transient_attempts < self.max_retries:
            self.enqueue()
            _logger.warning("Job %s failed, scheduling retry #%d: %s", self.name, self.retry_count, error_msg)
            return True
        _logger.error("Job %s failed permanently: %s", self.name, error_msg)
        return self._give_up(error_msg)

    def _give_up(self, error_msg: str) -> bool:
        """Fail this job permanently and cancel the rest of its batch. Returns False."""
        self.fail(error_msg)
        self._get_next_jobs().cancel(message=_("Previous job in batch failed"))
        return False

    @api.model
    def _is_transient_error(self, error: Exception | str) -> bool:
        """
        Whether ``error`` is a transient PostgreSQL concurrency failure
        (serialization failure, deadlock or lock-not-available), safe to retry once
        the contention clears. Reuses Odoo's canonical
        ``PG_CONCURRENCY_EXCEPTIONS_TO_RETRY`` set.

        Walks the exception chain (``__cause__`` and the implicit ``__context__``)
        so a failure re-raised/wrapped one or more levels deep is still recognized.
        A plain string (e.g. the "Job timed out" reaper message) is never transient.
        """
        seen: set[int] = set()
        exc = error if isinstance(error, BaseException) else None
        while exc is not None and id(exc) not in seen:
            seen.add(id(exc))
            if isinstance(exc, PG_CONCURRENCY_EXCEPTIONS_TO_RETRY):
                return True
            exc = exc.__cause__ or exc.__context__
        return False

    @api.model
    def _compute_backoff_delay(self, attempt: int) -> float:
        """
        Exponential backoff (seconds) with jitter, capped at 5 minutes. ``attempt``
        is 1-based.
        """
        base, ceiling, exp_cap = 5, 300, 8
        delay = min(ceiling, base * 2 ** min(attempt - 1, exp_cap))
        return delay + random.uniform(0, delay * 0.25)

    @api.model
    def _get_int_param(self, key: str, default: int) -> int:
        """
        Read an integer system parameter, falling back to ``default`` (with a
        warning) when the stored value is missing or not a valid integer, so a
        fat-fingered parameter cannot crash the runner cron on every tick.
        """
        value = self.env["ir.config_parameter"].sudo().get_param(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            _logger.warning("Invalid value %r for system parameter %s; using default %s.", value, key, default)
            return default

    @api.model
    def _get_transient_max_retries(self) -> int:
        """Retry budget for transient concurrency failures (separate from ``max_retries``)."""
        return max(1, self._get_int_param("base_bg.transient_max_retries", 10))

    @api.model
    def _get_max_concurrent_jobs(self) -> int:
        """
        Best-effort throttle on how many jobs may be ``running`` at once. ``0``
        (default) disables it, leaving concurrency untouched. Meant as a live
        emergency valve: raise ``base_bg.max_concurrent_jobs`` to dampen a
        contention storm without a deploy. It is best-effort, NOT a hard ceiling —
        concurrent acquirers reading the same snapshot can overshoot it by up to the
        number of runner workers.
        """
        return max(0, self._get_int_param("base_bg.max_concurrent_jobs", 0))

    @api.model
    def _get_cron_timeout(self) -> int:
        """
        The cron real-time limit in seconds (0 if unset), past which a still-
        ``running`` job is treated as a dead-worker orphan.
        """
        return tools.config.get("limit_time_real_cron") or 0

    @api.model
    def _can_acquire_job(self) -> bool:
        """
        Best-effort admission control: whether a new job may start under the
        ``base_bg.max_concurrent_jobs`` throttle (``0`` = disabled, the default).

        Jobs stuck ``running`` past the cron timeout (dead-worker orphans, which the
        monitor cron reaps) do not count toward the limit, so a couple of orphans
        cannot saturate the cap and starve the queue. Best-effort, not a hard
        ceiling: concurrent acquirers can overshoot by up to the number of workers.
        """
        cap = self._get_max_concurrent_jobs()
        if not cap:
            return True
        domain = [("state", "=", "running")]
        timeout = self._get_cron_timeout()
        if timeout:
            domain.append(("start_time", ">", fields.Datetime.now() - timedelta(seconds=timeout)))
        return self.search_count(domain, limit=cap) < cap

    @api.model
    def _has_eligible_jobs(self) -> bool:
        """Whether at least one enqueued job is past its backoff window."""
        return bool(
            self.search_count(
                [
                    ("state", "=", "enqueued"),
                    "|",
                    ("next_retry_at", "=", False),
                    ("next_retry_at", "<=", fields.Datetime.now()),
                ],
                limit=1,
            )
        )

    def _notify_user(self, result: str):
        """
        Notify user about job status

        :param result: The result of the job execution
        """
        channel = (
            self.env["discuss.channel"]
            .with_user(self.create_uid)
            .sudo()
            ._get_or_create_chat([self.create_uid.partner_id.id])
        )
        partner_root_id = self.env.ref("base.partner_root").id
        channel.message_post(
            body=Markup(result),
            author_id=partner_root_id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    def _get_next_jobs(self) -> "BgJob":
        """
        Get the next jobs in the same batch.

        :return: Recordset of next jobs in the batch
        """
        self.ensure_one()
        current_job = self
        jobs = self.env["bg.job"]
        while current_job.next_job_id:
            jobs |= current_job.next_job_id
            current_job = current_job.next_job_id
        return jobs

    @api.model
    def _get_next_job(self) -> "BgJob":
        """
        Retrieve the next enqueued job using optimistic locking.
        Uses SELECT FOR UPDATE SKIP LOCKED to avoid conflicts with other cron jobs.
        Not only grabs the next job, but also marks it as running.

        Under Odoo's default REPEATABLE READ isolation, SKIP LOCKED does not fully
        prevent conflicts: if a concurrent worker already grabbed and committed the
        head-of-queue row, this transaction (older snapshot) still selects it, the row
        is no longer locked so it is not skipped, and the UPDATE raises a
        SerializationFailure. This is expected under contention and handled by the
        caller (_cron_run_enqueued_jobs) with a bounded retry, so it must not be logged
        as a "bad query" ERROR — hence log_exceptions=False.

        Jobs still inside their ``next_retry_at`` backoff window are skipped. The
        gate uses a Python-computed UTC timestamp (matching Odoo's naive-UTC storage
        and ``fields.Datetime.now()``) rather than SQL ``NOW()``, whose result
        depends on the session time zone. Concurrency throttling is a separate
        concern handled by ``_can_acquire_job`` before this is called.

        :return: The next BgJob record to process, or an empty recordset if none available
        """
        self.env.cr.execute(
            """
            WITH candidate AS (
                SELECT id
                FROM bg_job
                WHERE state = 'enqueued'
                  AND (next_retry_at IS NULL OR next_retry_at <= %(now)s)
                ORDER BY priority, create_date, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE bg_job j
            SET state = 'running',
                start_time = %(now)s
            FROM candidate
            WHERE j.id = candidate.id
            RETURNING j.id;
            """,
            {"now": fields.Datetime.now()},
            log_exceptions=False,
        )
        row = self.env.cr.fetchone()
        return self.browse(row[0]) if row else self.env["bg.job"]

    @api.model
    def _cron_run_enqueued_jobs(self):
        """
        Execute one enqueued background job using optimistic locking.

        Uses SELECT FOR UPDATE SKIP LOCKED to allow multiple crons to safely
        pick up jobs without conflicts. Each cron processes one available job
        that isn't locked by other crons, naturally balancing the load.

        Retry on SerializationFailure (concurrent workers racing on the same row).
        Since no writes have been done yet at this point, rolling back and retrying
        in-process is safe and avoids the trigger storm caused by all workers
        surrendering at once and rescheduling each other.
        """
        if not self._can_acquire_job():
            return
        job = None
        for attempt in range(MAX_ACQUIRE_RETRIES):
            try:
                job = self._get_next_job()
                break
            except psycopg2.errors.SerializationFailure:
                self.env.cr.rollback()
                if attempt == MAX_ACQUIRE_RETRIES - 1:
                    _logger.warning(
                        "Failed to acquire next background job after %d attempts due to "
                        "concurrent workers; rescheduling.",
                        MAX_ACQUIRE_RETRIES,
                    )
                    self.env["base.bg"].sudo()._trigger_crons()
                    return
            except Exception:
                # Any other (unexpected) error leaves the transaction aborted; roll it
                # back so the cursor is clean before propagating, and do not retry.
                self.env.cr.rollback()
                raise

        if not job:
            return

        job.run()
        # Trigger cron again only if there are more *eligible* jobs to process.
        # Jobs waiting out their backoff window (next_retry_at in the future) must
        # NOT keep the cron re-triggering, or a backing-off job would spin the
        # scheduler in a tight loop and defeat the backoff.
        if self._has_eligible_jobs():
            self.env["base.bg"].sudo()._trigger_crons()

    @api.model
    def _cron_check_running_jobs(self):
        """Check running background jobs honoring the cron timeout (seconds)."""
        cutoff_date = fields.Datetime.now() - timedelta(seconds=self._get_cron_timeout())
        jobs = self.search(
            [
                ("start_time", "<", cutoff_date),
                ("state", "=", "running"),
            ]
        )
        for job in jobs:
            job._handle_job_error(_("Job timed out"))
            if job.state == "failed":
                message = _("Job %s timed out") % job._get_html_link(title=job.name)
                job._notify_user(message)
