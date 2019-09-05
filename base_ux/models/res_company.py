##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    active = fields.Boolean(
        default=True,
    )
