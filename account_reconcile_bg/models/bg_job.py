##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class BgJob(models.Model):
    _inherit = "bg.job"

    def cancel(self, message: str | None = None):
        """Override para limpiar el flag cuando se cancela el job."""
        res = super().cancel(message=message)
        self.filtered(
            lambda j: j.model == "account.bank.statement.line" and j.method == "_bg_validate_reconciliation"
        )._clean_reconciliation_flag()
        return res

    def fail(self, error_message: str):
        """Override para limpiar el flag cuando falla el job."""
        res = super().fail(error_message)
        self.filtered(
            lambda j: j.model == "account.bank.statement.line" and j.method == "_bg_validate_reconciliation"
        )._clean_reconciliation_flag()
        return res

    def _clean_reconciliation_flag(self):
        """Limpia el flag reconciliation_in_background para jobs de conciliación."""
        for job in self:
            kwargs = job.kwargs_json or {}
            # Limpiar flag de la línea de extracto
            record_ids = kwargs.get("_record_ids", [])
            if record_ids:
                lines = self.env["account.bank.statement.line"].browse(record_ids).exists()
                if lines:
                    lines.write({"reconciliation_in_background": False})
            # Limpiar flag de las líneas de pago (solo las que existen)
            selected_aml_ids = kwargs.get("selected_aml_ids", [])
            if selected_aml_ids:
                amls = self.env["account.move.line"].browse(selected_aml_ids).exists()
                if amls:
                    amls.write({"reconciliation_in_background": False})
