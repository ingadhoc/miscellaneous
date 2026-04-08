# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class BgJob(models.Model):
    _inherit = "bg.job"

    def action_retry_batch(self):
        """
        Action to retry multiple failed jobs at once
        """
        failed_jobs = self.filtered(lambda j: j.state == "failed")
        if not failed_jobs:
            raise UserError(_("Please select only failed jobs to retry"))

        other_jobs = self - failed_jobs
        if other_jobs:
            raise UserError(_("Some selected jobs are not in failed state and cannot be retried"))

        failed_jobs.write(
            {
                "state": "enqueued",
                "retry_count": 0,
                "error_message": False,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Jobs Requeued"),
                "type": "success",
                "message": _("%s job(s) have been requeued for retry") % len(failed_jobs),
                "sticky": False,
            },
        }
