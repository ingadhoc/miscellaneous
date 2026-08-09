from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    iot_device_id = fields.Many2one(
        comodel_name="iot.device",
        string="Default Printer",
        domain="[('type', '=', 'printer')]",
    )
