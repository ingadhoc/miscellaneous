from odoo import Command

from .common import SheetMappingCase


class TestAutoReconcile(SheetMappingCase):
    def test_automatic_models_run_on_import(self):
        """A line matched by an automatic model is reconciled by the import itself, not by the daily cron."""
        if self.env["ir.module.module"]._get("account_accountant").state != "installed":
            self.skipTest("the automatic reconciliation on create comes with account_accountant")
        account = self.env["account.account"].create(
            {"name": "Tax on bank debits", "code": "UX25413", "account_type": "expense"}
        )
        self.env["account.reconcile.model"].create(
            {
                "name": "25413",
                "trigger": "auto_reconcile",
                "match_journal_ids": [Command.set(self.journal.ids)],
                "match_label": "contains",
                "match_label_param": "25413",
                "line_ids": [Command.create({"account_id": account.id})],
            }
        )
        data_file = self.sheet(
            [
                ("01/10/2026", "Imp. Ley 25413 debito", "-120,50", "1.000,00"),
                ("01/10/2026", "Transferencia recibida", "500,00", "1.500,00"),
            ]
        )
        result = self.import_wizard(data_file)._import_file()
        lines = self.env["account.bank.statement"].browse(result["statement_ids"]).line_ids
        self.assertRecordValues(
            lines.sorted("payment_ref"),
            [
                {"payment_ref": "Imp. Ley 25413 debito", "is_reconciled": True},
                {"payment_ref": "Transferencia recibida", "is_reconciled": False},
            ],
        )
