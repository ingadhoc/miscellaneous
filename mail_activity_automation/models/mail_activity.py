import datetime
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _cron_run_activities(self):
        activities = self.search(
            [
                ("activity_type_id.run_automatically", "=", True),
                ("date_deadline", "<=", datetime.date.today()),
                ("res_model", "!=", False),
                ("res_id", "!=", False),
            ]
        )
        for activity in activities:
            try:
                with self.env.cr.savepoint():
                    activity._run_automatically()
            except Exception:
                # one failing activity must not roll back the others
                _logger.exception("Automatic run of activity %s failed", activity.id)

    def _run_automatically(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        for mail_template in self.activity_type_id.mail_template_ids:
            record.message_post_with_source(mail_template, subtype_xmlid="mail.mt_comment")
        self._action_done()
