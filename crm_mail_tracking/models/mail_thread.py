from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _add_extra_recipients_suggestions(self, suggestions, field_mail, reason):
        """
        Agregamos este método debido a que cuando en el CRM no hay un email_from, al
        llamar a _message_partner_info_from_emails termina dando error porque no verifica
        si tiene un email_from y utiliza email_from.lower()
        """
        if not (self._name == 'crm.lead' and not self.email_from):
            super()._add_extra_recipients_suggestions(self, suggestions, field_mail, reason)
