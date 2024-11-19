

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def behaviour(self):
        # Parche ADHOC por PR: https://github.com/OCA/report-print-send/pull/367
        self = self.with_context(skip_printer_exception=True)
        return super().behaviour()
