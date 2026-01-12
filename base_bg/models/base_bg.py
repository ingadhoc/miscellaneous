##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from odoo import _, api, models
from odoo.models import BaseModel

if TYPE_CHECKING:
    from base_bg.models.bg_job import BgJob


class BaseBg(models.AbstractModel):
    _name = "base.bg"
    _description = "Background Job Mixin"

    @api.model
    def bg_enqueue_records(
        self, records: models.BaseModel, method: str, threshold: int | None = None, *args, **kwargs
    ) -> tuple[dict, "BgJob"]:
        """
        Enqueue background jobs in batches based on record threshold.

        This is a model/API method and must be called on the model, passing
        the target records as the first argument. Example:
            self.env['base.bg'].bg_enqueue(records, 'method_name', threshold=..., ...)

        :param method: The method name to execute on each batch
        :param records: recordset or iterable of ids (or None) representing targets
        :param threshold: Maximum number of records per job
        :param args: Positional arguments for the method
        :param kwargs: Keyword arguments for the method
            :param priority: Job priority (default: 10)
            :param max_retries: Maximum retries for the job (default: 3)
        :return: A display notification and the created jobs
        """
        # Normalize records into ids; allow None/empty to mean no targets
        jobs = self.env["bg.job"]
        model = records._name
        record_ids = records.ids if records else []
        priority = max(kwargs.pop("priority", 10), 0)
        max_retries = kwargs.pop("max_retries", 3)
        name = kwargs.get("name", "")

        def _get_name(batch_id: str, queue_order: int) -> str:
            return name or "%s.%s-%s-%s" % (model, method, batch_id[0:8], queue_order)

        batch_id = str(uuid.uuid4())
        total = len(record_ids) or 1
        threshold = threshold or total
        threshold = max(1, int(threshold))
        prev_job = None
        for i in range(0, total, threshold):
            chunk_ids = record_ids[i : i + threshold]
            queue_order = i // threshold
            context = {k: self._json_safe(v) for k, v in self.env.context.items()}
            job_vals = {
                "name": _get_name(batch_id, queue_order),
                "model": model,
                "method": method,
                "priority": priority,
                "max_retries": max_retries,
                "context_json": context,
                "batch_id": batch_id,
                "state": "enqueued" if queue_order == 0 else "waiting",
            }
            kwargs["_record_ids"] = list(chunk_ids) if chunk_ids else []
            job_vals["args_json"] = list(args) if args else []
            job_vals["kwargs_json"] = kwargs
            job = self.env["bg.job"].create(job_vals)
            jobs |= job
            # Link previous job to current so sequence is established in one pass
            if prev_job:
                prev_job.next_job_id = job.id
            prev_job = job

        self.sudo()._trigger_crons()
        title = _("Processes sent to background successfully")
        message = _("You will be notified when they are done.")
        return (
            {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": title,
                    "type": "success",
                    "message": message,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            },
            jobs,
        )

    def bg_enqueue(self, method: str, threshold: int | None = None, *args, **kwargs) -> tuple[dict, "BgJob"]:
        """
        Instance-style enqueuing helper.

        Usage:
            _inherit = ['base.bg', ...]
            ...
            records.bg_enqueue('method_name', threshold=..., ...)

        Delegates to the model API `bg_enqueue_records` using the calling
        recordset as the `records` parameter.
        """
        return self.bg_enqueue_records(self, method, threshold, *args, **kwargs)

    def _trigger_crons(self):
        """
        Trigger cron jobs to process enqueued background jobs
        """
        code = "_cron_run_enqueued_jobs("
        crons = self.env["ir.cron"].search([("code", "ilike", code)])
        for cron in crons:
            cron._trigger()

    @api.model
    def _json_safe(self, value : Any) -> Any:
        """
        Convert a value into a JSON-serializable format.

        :param value: The value to convert
        :return: A JSON-serializable representation of the value
        """
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, (date, datetime, time)):
            return value.isoformat()

        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(v) for v in value]

        if isinstance(value, dict):
            return {
                str(k): self._json_safe(v)
                for k, v in value.items()
            }

        # Odoo recordsets
        if isinstance(value, BaseModel):
            return value.ids

        # fallback seguro
        return str(value)
