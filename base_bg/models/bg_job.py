##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
from datetime import timedelta

import psycopg2
from markupsafe import Markup
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain

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
        help="Current number of retry attempts",
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
        Executes the job
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
        """Mark the job as enqueued."""
        data: dict[str, str | int | bool] = {
            "state": "enqueued",
        }
        if retry:
            data.update(
                {
                    "retry_count": 0,
                    "error_message": False,
                }
            )
        self.write(data)

    def finish(self):
        """
        Mark the job as done and set the end time.
        Also enqueue the next job in the batch if it exists.
        """
        self.write(
            {
                "state": "done",
                "end_time": fields.Datetime.now(),
            }
        )
        self.filtered("next_job_id").mapped("next_job_id").enqueue()
        self.env["base.bg"].sudo()._trigger_crons()

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

    def _handle_job_error(self, error: Exception | str):
        """
        Handle job execution error

        :param error: The exception raised during job execution
        """
        error_msg = str(error)
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            self.enqueue()
            _logger.warning("Job %s failed, scheduling retry #%d: %s", self.name, self.retry_count, error_msg)
        else:
            # Max retries reached, mark as failed
            self.fail(error_msg)
            self._get_next_jobs().cancel(message=_("Previous job in batch failed"))
            _logger.error("Job %s failed permanently: %s", self.name, error_msg)

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

        :return: The next BgJob record to process, or an empty recordset if none available
        """
        self.env.cr.execute(
            """
            WITH candidate AS (
                SELECT id
                FROM bg_job
                WHERE state = 'enqueued'
                ORDER BY priority, create_date, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE bg_job j
            SET state = 'running',
                start_time = NOW()
            FROM candidate
            WHERE j.id = candidate.id
            RETURNING j.id;
            """,
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
        # Trigger cron again if there are more jobs to process
        if self.search_count(Domain("state", "=", "enqueued")):
            self.env["base.bg"].sudo()._trigger_crons()

    @api.model
    def _cron_check_running_jobs(self):
        """Check running background jobs honoring the cron timeout (seconds)."""
        timeout_seconds = tools.config.get("limit_time_real_cron") or 0
        cutoff_date = fields.Datetime.now() - timedelta(seconds=timeout_seconds)
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
