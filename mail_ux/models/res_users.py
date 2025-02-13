from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    send_message_delay = fields.Integer()
