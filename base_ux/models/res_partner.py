##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    active = fields.Boolean(tracking=True)
    mobile = fields.Char(tracking=True)
