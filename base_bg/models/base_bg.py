import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class BaseBg(models.AbstractModel):
    _name = "base.bg"
    _description = "Background Job Mixin"

    @api.model
    def bg_enqueue(self, method: str, *args, **kwargs):
        """
        Enqueue a background job for execution.

        :param method: The method name to execute

        Special kwargs:
            :param max_retries: Maximum retry attempts (default: 3)

        :return: A display notification
        """
        max_retries = kwargs.pop("max_retries", 3)
        name = kwargs.pop("name", f"{self._name}.{method}")
        job_vals = {
            "name": name,
            "model": self._name,
            "method": method,
            "max_retries": max_retries,
            "context_json": dict(self.env.context),
        }

        # Handle recordset: store IDs for later reconstruction
        if self:
            kwargs["_record_ids"] = self.ids

        # Serialize arguments
        job_vals["args_json"] = list(args) if args else []
        job_vals["kwargs_json"] = kwargs
        self.env["bg.job"].create(job_vals)
        self.sudo()._trigger_crons()
        title = _("Process sent to background successfully")
        message = _("You will be notified when it is done.")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "type": "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _trigger_crons(self):
        """
        Trigger cron jobs to process enqueued background jobs
        """
        code = "_cron_run_enqueued_jobs("
        crons = self.env["ir.cron"].search([("code", "ilike", code)])
        for cron in crons:
            cron._trigger()
