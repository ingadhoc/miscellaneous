from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    statement_import_auto_reconcile = fields.Boolean(
        string="Reconcile on Statement Import",
        default=True,
        help="When a statement file is imported, try to reconcile its lines right away, "
        "the same way the automatic reconciliation cron does: it matches invoices and "
        "payments of the same partner by amount and applies the automatic reconciliation "
        "models. Needs Accounting (Enterprise). When unchecked, the imported lines wait "
        "for the cron or for somebody to reconcile them.",
    )
