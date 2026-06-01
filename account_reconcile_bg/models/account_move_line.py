##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    reconciliation_in_background = fields.Boolean(
        string="Reconciliation in Background",
        readonly=True,
        help="Indicates that this line is being reconciled in background",
    )
