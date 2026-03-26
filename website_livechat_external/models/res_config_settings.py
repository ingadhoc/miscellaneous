from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    external_livechat_enabled = fields.Boolean(
        string="Habilitar LiveChat Externo",
        config_parameter="website_livechat_external.enabled",
    )
    external_livechat_provider_url = fields.Char(
        string="URL del Proveedor",
        config_parameter="website_livechat_external.provider_url",
        help=(
            "URL base de la instancia Odoo externa que provee el livechat. "
            "Ejemplo: https://train-adhoc-25-03-1.adhoc.inc"
        ),
    )
    external_livechat_channel_id = fields.Integer(
        string="ID del Canal",
        config_parameter="website_livechat_external.channel_id",
        help="ID numérico del canal de livechat en la instancia proveedora.",
    )