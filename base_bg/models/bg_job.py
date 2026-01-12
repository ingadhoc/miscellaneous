##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
from datetime import timedelta
from typing import Optional

from markupsafe import Markup
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain

_logger = logging.getLogger(__name__)


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
            ("waiting", "Waiting"),
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
    batch_id = fields.Char(
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
    batch_job_count = fields.Integer(
        string="Jobs in Batch",
        compute="_compute_batch_info",
        help="Total number of jobs in this batch",
    )
    batch_progress_count = fields.Integer(
        compute="_compute_batch_info",
        help="Total number of jobs completed in this batch",
    )

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for job in self:
            if job.start_time and job.end_time:
                delta = job.end_time - job.start_time
                job.duration = delta.total_seconds()
            else:
                job.duration = 0.0

    @api.depends("batch_id", "state")
    def _compute_batch_info(self):
        batch_ids = set(self.mapped("batch_id"))
        if not batch_ids:
            return

        for batch_id in batch_ids:
            jobs_in_batch = self.search(Domain("batch_id", "=", batch_id))
            total = len(jobs_in_batch)
            done_count = sum(1 for j in jobs_in_batch if j.state == "done")
            jobs_in_batch.write(
                {
                    "batch_job_count": total,
                    "batch_progress_count": done_count,
                }
            )

    def action_cancel(self):
        """
        Action to manually cancel enqueued jobs
        """
        self.ensure_one()
        if self.state != "enqueued":
            raise UserError(_("Only enqueued jobs can be canceled"))
        self.write(
            {
                "state": "canceled",
                "cancel_time": fields.Datetime.now(),
            }
        )

    def action_retry(self):
        """
        Action to manually retry failed job
        """
        self.ensure_one()
        if self.state != "failed":
            raise UserError(_("Only failed jobs can be retried"))
        self.write(
            {
                "state": "enqueued",
                "retry_count": 0,
                "error_message": False,
            }
        )

    def action_open_records(self) -> dict:
        """
        Action to open the records related to the job
        """
        self.ensure_one()
        model = self.env[self.model]
        kwargs = self.kwargs_json or {}
        record_ids = kwargs.get("_record_ids", None)
        records = model.browse(record_ids) if record_ids else model.browse()
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
            "name": _("Batch Jobs: %s", self.batch_id[:8]),
            "type": "ir.actions.act_window",
            "res_model": "bg.job",
            "view_mode": "list,form",
            "domain": [("batch_id", "=", self.batch_id)],
            "context": {"search_default_batch_id": self.batch_id},
        }

    def run(self):
        """
        Executes the job
        """
        self.ensure_one()
        if self.state != "enqueued":
            raise UserError(_("Only enqueued jobs can be executed"))

        self.write(
            {
                "state": "running",
                "start_time": fields.Datetime.now(),
            }
        )
        self.env.cr.commit()  # pylint: disable=invalid-commit

        try:
            context = self.context_json or {}
            context.update({"bg_job": True, "bg_job_id": self.id})

            # Extract record IDs if present in kwargs or args
            model = self.env[self.model]
            args = self.args_json or []
            kwargs = self.kwargs_json or {}
            record_ids = kwargs.pop("_record_ids", None)
            records = model.browse(record_ids).with_context(**context).with_user(self.create_uid)
            result = getattr(records, self.method)(*args, **kwargs)

            self.write(
                {
                    "state": "done",
                    "end_time": fields.Datetime.now(),
                }
            )
            if result:
                self._notify_user(result)
                self.env.cr.commit()  # pylint: disable=invalid-commit
            if self.next_job_id:
                self.next_job_id.state = "enqueued"
        except Exception as e:
            self.env.cr.rollback()  # pylint: disable=invalid-commit
            self._handle_job_error(e)
            raise

    def _handle_job_error(self, error: Exception | str):
        """
        Handle job execution error

        :param error: The exception raised during job execution
        """
        error_msg = str(error)
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            self.write(
                {
                    "state": "enqueued",
                }
            )
            _logger.warning("Job %s failed, scheduling retry #%d: %s", self.name, self.retry_count, error_msg)
        else:
            # Max retries reached, mark as failed
            self.write(
                {
                    "state": "failed",
                    "end_time": fields.Datetime.now(),
                    "error_message": error_msg,
                }
            )
            self._get_next_jobs().write(
                {
                    "state": "canceled",
                    "cancel_time": fields.Datetime.now(),
                    "error_message": _("Canceled due to previous job failure in batch"),
                }
            )
            _logger.error("Job %s failed permanently: %s", self.name, error_msg)

    def _notify_user(self, result: str):
        """
        Notify user about job status

        :param result: The result of the job execution
        """
        channel = (
            self.env["discuss.channel"].with_user(self.create_uid)._get_or_create_chat([self.create_uid.partner_id.id])
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
    def _get_next_job(self) -> Optional["BgJob"]:
        """
        Get and lock the next available enqueued job atomically.
        Uses SELECT FOR UPDATE SKIP LOCKED to safely acquire a job without race conditions.

        For batch jobs (jobs with batch_id):
        - A batch job can only execute if the previous job in the same batch is done
        - If the previous job is not done yet, the job is skipped

        :return: Returns the locked job or an empty recordset.
        """
        enqueued_jobs = self.search(
            Domain("state", "=", "enqueued"),
        )
        for job in enqueued_jobs:
            self.env.cr.execute(
                """
                SELECT id FROM bg_job
                WHERE id = %s AND state = 'enqueued'
                FOR UPDATE SKIP LOCKED
                """,
                (job.id,),
            )
            result = self.env.cr.fetchone()
            if result:
                # Successfully locked the job
                return self.browse(result[0])
            # If we couldn't lock it, continue to the next candidate

        return None

    @api.model
    def _cron_run_enqueued_jobs(self):
        """
        Execute one enqueued background job using optimistic locking.

        Uses SELECT FOR UPDATE SKIP LOCKED to allow multiple crons to safely
        pick up jobs without conflicts. Each cron processes one available job
        that isn't locked by other crons, naturally balancing the load.
        """
        job = self._get_next_job()
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
