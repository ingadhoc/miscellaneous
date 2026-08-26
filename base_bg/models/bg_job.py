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
        help="Attempts lost to transient DB contention, counted separately from the normal retry budget.",
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
        help="Earliest time this job may be retried after a transient failure.",
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

        Retried on transient failures, so the method may run more than once
        (at-least-once); side-effecting methods should be idempotent.

        The ORM cache is dropped after each job (``invalidate_all``): the runner
        loops many jobs inside one long-lived cron process, so releasing each job's
        cache flattens the runner's memory curve between jobs.
        """
        self.ensure_one()
        if self.state != "running":
            raise UserError(_("Only running jobs can be executed"))

        if self._cancel_if_orphaned():
            return

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
            self.env.invalidate_all()
        except Exception as e:
            self.env.cr.rollback()  # pylint: disable=invalid-commit
            self.env.invalidate_all()
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
        Mark the job as done and enqueue the next job in the batch.

        The cron is NOT triggered here: ``_cron_run_enqueued_jobs`` re-triggers
        itself while eligible jobs remain, so triggering per finish only churns
        ``ir_cron`` under load.
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
            # exists(): a job can outlive its records, and browsing a dropped id is truthy —
            # _get_html_link() reads display_name on it and would raise MissingError.
            records = self._get_records().exists()
            if records:
                links = [record._get_html_link() for record in records]
                message += "<br/>" + _("Related records: %s") % (", ".join(links))
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

    def _cancel_if_orphaned(self) -> bool:
        """
        Cancel this job (and the rest of its batch) when every record it points to is gone.

        A job can outlive its records (a GC or an FK cascade wins the race). Such a job did
        not fail — there is nothing left to run it on — so it is canceled instead of failed,
        keeping failure metrics and notifications meaningful. Jobs that point to no records
        at all (model-level methods) are not orphans.

        :return: True if the job was canceled as an orphan
        """
        self.ensure_one()
        records = self._get_records()
        if not records or records.exists():
            return False
        _logger.info("Job %s canceled: the records it points to no longer exist", self.name)
        self.cancel(message=_("The records of this job no longer exist"))
        self._get_next_jobs().cancel(message=_("Previous job in batch was canceled"))
        return True

    def _handle_job_error(self, error: Exception | str) -> bool:
        """
        Handle a job execution error and decide whether to retry.

        Transient DB contention (serialization / deadlock / lock timeout) is retried
        with exponential backoff on its own budget (``transient_retry_count`` vs
        ``base_bg.transient_max_retries``), separate from ``max_retries`` so a
        contention spike does not consume the retries meant for real errors. Other
        errors keep the immediate-retry-then-fail behavior. ``retry_count`` tracks
        every attempt (for display); the non-transient budget is measured on
        non-transient attempts.

        :return: True if re-enqueued, False if failed permanently (overrides use this).
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
                # Wake a runner when the backoff elapses (a backing-off job is
                # skipped by the self-retrigger, so nothing else would).
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
        Whether ``error`` is a transient PG concurrency failure, safe to retry.
        Reuses Odoo's ``PG_CONCURRENCY_EXCEPTIONS_TO_RETRY`` and walks the
        ``__cause__`` / ``__context__`` chain so a wrapped failure is still caught.
        A plain string (the reaper's "Job timed out") is never transient.
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
        Read an int system parameter, falling back to ``default`` (with a warning)
        on a missing or non-integer value, so a bad param cannot crash the runner.
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

        Backed-off jobs (``next_retry_at`` in the future) are skipped, using a Python
        UTC timestamp rather than SQL ``NOW()`` (which is session-tz dependent).

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
        # Re-trigger only if more *eligible* jobs remain: a backing-off job
        # (next_retry_at in the future) must not spin the scheduler.
        if self._has_eligible_jobs():
            self.env["base.bg"].sudo()._trigger_crons()

    @api.model
    def _get_reaper_timeout(self) -> int:
        """
        Effective real-time limit (seconds) for cron-run jobs, mirroring how the
        server resolves ``limit_time_real_cron`` in each mode:

        - prefork (``workers`` > 0): ``0``/unset means no limit, ``-1`` delegates
          to ``--limit-time-real`` (``PreforkServer.__init__``).
        - threaded (``workers`` == 0): the value only applies when > 0, anything
          else falls back to ``--limit-time-real`` (``ThreadedServer.process_limit``).

        :return: the limit, or 0 when there is none.
        """
        timeout = tools.config.get("limit_time_real_cron") or 0
        if timeout > 0:
            return timeout
        if timeout == -1 or not tools.config.get("workers"):
            return tools.config.get("limit_time_real") or 0
        return 0

    @api.model
    def _cron_check_running_jobs(self):
        """
        Time out running jobs past the cron real-time limit, and cancel orphaned ones.

        The orphan sweep is independent of the time limit: a running job whose
        records are gone can never finish on its own, so it is swept even when no
        limit is configured and nothing can ever time out.
        """
        timeout_seconds = self._get_reaper_timeout()
        cutoff_date = fields.Datetime.now() - timedelta(seconds=timeout_seconds) if timeout_seconds > 0 else None
        jobs = self.search([("state", "=", "running")])
        timeout_msg = _("Job timed out")
        for job in jobs:
            job_name = job.name
            overdue = bool(cutoff_date and job.start_time and job.start_time < cutoff_date)
            try:
                # Per-job savepoint: a job that raises would otherwise abort the whole reaper
                # and leave every other timed-out job running forever.
                with self.env.cr.savepoint():
                    if job._cancel_if_orphaned():
                        continue
                    if not overdue:
                        continue
                    job._handle_job_error(timeout_msg)
                    if job.state == "failed":
                        job._notify_user(_("Job %s timed out") % job._get_html_link(title=job_name))
            except Exception as error:
                # No invalidation needed: the savepoint rollback already cleared the cache
                # and the pending updates (_FlushingSavepoint.rollback -> cr.clear()).
                if self._is_transient_error(error):
                    _logger.warning("Job %s not timed out yet, transient error: %s", job_name, error)
                    continue
                if not overdue:
                    # The bare-fail recovery below is for jobs already past their limit;
                    # a job that merely failed its orphan check keeps running.
                    _logger.exception("Could not check job %s, leaving it for the next run", job_name)
                    continue
                _logger.exception("Could not time out job %s, giving up on it", job_name)
                try:
                    # Own savepoint: the recovery path writes through the registry too, so a
                    # model override raising here would abort the whole reaper as well.
                    with self.env.cr.savepoint():
                        # Base implementations on purpose: the rollback restored the job to
                        # running and whatever the model added on top is what just raised.
                        BgJob.fail(job, timeout_msg, notify=False)
                        job._get_next_jobs().cancel(message=_("Previous job in batch failed"))
                except Exception as fallback_error:
                    if self._is_transient_error(fallback_error):
                        _logger.warning("Job %s not failed yet, transient error: %s", job_name, fallback_error)
                    else:
                        _logger.exception("Could not fail job %s either, leaving it for the next run", job_name)
