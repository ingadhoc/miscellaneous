from datetime import datetime, timedelta

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _action_send_mail(self, auto_commit=False):
        """
        Heredado para incluir un retraso de x segundos al enviar mensajes si está configurado en el perfil.
        """
        if self.env.user.send_message_delay:
            scheduled_date = datetime.now() + timedelta(seconds=self.env.user.send_message_delay)
            self.action_schedule_message(scheduled_date=scheduled_date)
            result_mails_su, result_messages = self.env["mail.mail"].sudo(), self.env["mail.message"]
        else:
            result_mails_su, result_messages = super(MailComposeMessage, self)._action_send_mail(
                auto_commit=auto_commit
            )
        return result_mails_su, result_messages
