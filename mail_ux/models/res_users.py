from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    send_message_delay = fields.Integer(
        help="Segundos que Odoo espera antes de enviar tus mensajes del chatter. "
        "Durante ese lapso el envío queda pendiente y podés cancelarlo; "
        "en 0 el mensaje se envía en el momento.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["send_message_delay"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["send_message_delay"]
