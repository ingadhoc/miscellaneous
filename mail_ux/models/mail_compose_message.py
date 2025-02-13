from datetime import datetime, timedelta

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _action_send_mail(self, auto_commit=False):
        """
        Heredado para incluir un retraso de x segundos al enviar mensajes.
        """
        result_mails_su, result_messages = super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
        if self.env.user.send_message_delay:
            scheduled_date = datetime.now() + timedelta(seconds=self.env.user.send_message_delay)
            if self.composition_mode != "mass_mail":
                for wizard in self:
                    res_ids = wizard._evaluate_res_ids()
                    for res_id in res_ids:
                        self.env["mail.scheduled.message"].create(
                            {
                                "attachment_ids": [(6, 0, wizard.attachment_ids.ids)],
                                "author_id": self.env.user.partner_id.id,
                                "body": wizard.body,
                                "model": wizard.model,
                                "res_id": res_id,
                                "partner_ids": [(6, 0, wizard.partner_ids.ids)],
                                "scheduled_date": scheduled_date,
                                "subject": wizard.subject,
                                "notification_parameters": "{}",
                            }
                        )

        return result_mails_su, result_messages
