from datetime import datetime, timedelta

from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    # Technical fields: remember what the attachments were generated from, so a
    # round trip that does not change those values reuses them.
    attachments_source_key = fields.Char(copy=False)
    attachments_source_ids = fields.Many2many(
        "ir.attachment",
        "mail_compose_message_source_attachment_rel",
        "wizard_id",
        "attachment_id",
        copy=False,
    )

    def _get_attachments_source_key(self):
        """Signature of the values _compute_attachment_ids generates from."""
        self.ensure_one()
        return repr(
            (
                self.composition_mode,
                self.model,
                self.res_domain,
                self.res_ids,
                self.template_id.id,
            )
        )

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_attachment_ids(self):
        """Do not render the template reports again when nothing changed.

        The field is a stored compute, so the web client invalidates it on every
        onchange round trip that sends back one of its dependencies, even when
        the value is the same. Each pass called _render_qweb_pdf again: opening
        the wizard once could run wkhtmltopdf several times, and each run needs
        a free worker to serve itself the report assets.
        """
        todo = self.browse()
        for composer in self:
            if composer.attachments_source_key == composer._get_attachments_source_key():
                composer.attachment_ids = composer.attachments_source_ids
            else:
                todo |= composer
        super(MailComposeMessage, todo)._compute_attachment_ids()
        for composer in todo:
            composer.attachments_source_key = composer._get_attachments_source_key()
            composer.attachments_source_ids = composer.attachment_ids

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

        # Limpiamos __action_done porque odoo guarda una base automation ahi
        # Al querer crear el mensaje programado falla por mala definicion de contexto (es un objeto y no un str, int, etc.)
        # No es replicable en odoo porque no tienen base automation para schedulear un mensaje
        self.with_context(__action_done={})._action_schedule_message()
        return self.env["mail.mail"].sudo(), self.env["mail.message"]
