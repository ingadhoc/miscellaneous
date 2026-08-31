##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class BgJob(models.Model):
    _inherit = "bg.job"

    def cancel(self, message: str | None = None):
        res = super().cancel(message=message)
        self._clear_reconciliation_bg_flag()
        return res

    def fail(self, error_message: str, notify: bool = True):
        res = super().fail(error_message, notify=notify)
        self._clear_reconciliation_bg_flag()
        return res

    def _clear_reconciliation_bg_flag(self):
        for job in self.filtered(
            lambda j: j.model == "account.bank.statement.line"
            and j.method == "_bg_set_batch_payment_bank_statement_line"
        ):
            self.env["account.bank.statement.line"].browse(
                (job.kwargs_json or {}).get("_record_ids", [])
            ).exists().write({"reconciliation_in_background": False})
