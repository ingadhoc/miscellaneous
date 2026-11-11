from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    statement_import_auto_reconcile = fields.Boolean(
        related="company_id.root_id.statement_import_auto_reconcile",
        readonly=False,
    )
