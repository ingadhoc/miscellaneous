from datetime import datetime, timedelta

from odoo import fields, models

REPORT_CACHE_PREFIX = "mail_ux.report_cache:"


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _compute_attachment_ids(self):
        """Heredado para no volver a renderizar el reporte en cada onchange.

        ``attachment_ids`` es un compute ``store=True, readonly=False``, así que el
        webclient lo recalcula en cada round-trip mientras se abre el compositor, y cada
        recálculo vuelve a llamar a ``_render_qweb_pdf``. Medido en producción: el mismo
        PDF generado de 2 a 6 veces por apertura del wizard, con los attachments
        huérfanos correspondientes tirados en la base.

        Reusamos el attachment ya generado mientras siga siendo del mismo reporte, del
        mismo registro y de una versión del registro no menos vieja que el PDF.
        """
        cacheable = self.browse()
        keys = {}
        for composer in self:
            key = composer._get_report_attachment_cache_key()
            if key:
                keys[composer.id] = key
                cacheable |= composer

        super(MailComposeMessage, self - cacheable)._compute_attachment_ids()

        for composer in cacheable:
            key = keys[composer.id]
            attachment = composer._find_cached_report_attachment(key)
            if attachment:
                composer.attachment_ids = composer.template_id.attachment_ids | attachment
                continue
            super(MailComposeMessage, composer)._compute_attachment_ids()
            composer._label_cached_report_attachment(key)

    def _get_report_attachment_cache_key(self):
        """Clave de reuso del PDF del reporte, o False si no corresponde cachear.

        Solo cacheamos el caso que dispara el problema y que además es inequívoco: modo
        comment monorecord, con un único reporte qweb en el template. Con más de un
        reporte no podemos asociar cada attachment creado con su reporte sin ambigüedad,
        así que dejamos que resuelva el core.
        """
        self.ensure_one()
        if not self._get_report_attachment_cache_ttl():
            return False
        template = self.template_id
        if not template or self.composition_mode != "comment" or self.composition_batch:
            return False
        if len(template.report_template_ids) != 1:
            return False
        report = template.report_template_ids
        if report.report_type not in ("qweb-html", "qweb-pdf"):
            return False
        res_ids = self._evaluate_res_ids() or []
        if len(res_ids) != 1 or not res_ids[0]:
            return False
        record = self.env[template.model].browse(res_ids[0]).exists()
        if not record:
            return False
        return "%s%s:%s:%s:%s:%s" % (
            REPORT_CACHE_PREFIX,
            report.id,
            template.model,
            record.id,
            fields.Datetime.to_string(record.write_date),
            self.env.context.get("lang") or self.env.user.lang or "",
        )

    def _get_report_attachment_cache_ttl(self):
        """Segundos durante los que se reusa un PDF ya generado. En 0 queda desactivado.

        Acota la ventana en la que un cambio que el reporte muestra pero que no toca la
        ``write_date`` del propio registro (datos del partner, de la compañía, una
        traducción) podría verse viejo.
        """
        return int(self.env["ir.config_parameter"].sudo().get_param("mail_ux.report_attachment_cache_ttl", 600))

    def _find_cached_report_attachment(self, key):
        limit_date = fields.Datetime.now() - timedelta(seconds=self._get_report_attachment_cache_ttl())
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "mail.compose.message"),
                ("res_id", "=", 0),
                ("create_uid", "=", self.env.uid),
                ("description", "=", key),
                ("create_date", ">=", fields.Datetime.to_string(limit_date)),
            ],
            limit=1,
        )

    def _label_cached_report_attachment(self, key):
        """Marca el attachment recién generado para poder reusarlo en el próximo
        recálculo. Si el core generó más de uno (por el hook de contabilidad, por
        ejemplo) no marcamos nada y el reuso simplemente no aplica."""
        self.ensure_one()
        new_attachments = self.attachment_ids.filtered(
            lambda attachment: attachment.res_model == "mail.compose.message"
            and not attachment.res_id
            and not attachment.description
        )
        if len(new_attachments) == 1:
            new_attachments.description = key

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
