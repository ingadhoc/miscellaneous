from datetime import datetime, timedelta

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _manage_mail_values(self, mail_values_all):
        """
        Heredado para incluir un retraso de x segundos al enviar mensajes si está configurado en el perfil.
        """
        mail_values_all = super()._manage_mail_values(mail_values_all)
        if not self.env.user.send_message_delay:
            return mail_values_all

        scheduled_date = datetime.now() + timedelta(seconds=self.env.user.send_message_delay)
        for res_id, mail_values in mail_values_all.items():
            mail_values["scheduled_date"] = scheduled_date
        return mail_values_all

    def _action_send_mail(self, auto_commit=False):
        """
        Cambio de logica: si hay un retraso configurado, se programa el envío en lugar de enviarlo inmediatamente.
        """
        if not self.env.user.send_message_delay:
            return super()._action_send_mail(auto_commit=auto_commit)

        self.action_schedule_message()
        return self.env["mail.mail"].sudo(), self.env["mail.message"]
