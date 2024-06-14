from odoo import models
import datetime


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _cron_run_activities(self):
        activities = self.search([('activity_type_id.run_automatically', '=', True), ('date_deadline', '<=', datetime.date.today())])
        for activity in activities:
            activity.with_context(from_bot=True).action_done_schedule_next()

    def _action_done(self, feedback=False, attachment_ids=None):
        if self._context.get('from_bot') and self.activity_type_id.mail_template_ids:
            for mail_template in self.activity_type_id.mail_template_ids:
                self.env[self.res_model].browse(self.res_id).message_post_with_source(
                    mail_template,
                    subtype_xmlid='mail.mt_comment'
                )
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
