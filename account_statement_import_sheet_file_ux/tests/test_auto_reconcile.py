from odoo import Command

from .common import SheetMappingCase


class TestAutoReconcile(SheetMappingCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        account = cls.env["account.account"].create(
            {"name": "Tax on bank debits", "code": "UX25413", "account_type": "expense"}
        )
        cls.env["account.reconcile.model"].create(
            {
                "name": "25413",
                "trigger": "auto_reconcile",
                "match_journal_ids": [Command.set(cls.journal.ids)],
                "match_label": "contains",
                "match_label_param": "25413",
                "line_ids": [Command.create({"account_id": account.id})],
            }
        )

    def setUp(self):
        super().setUp()
        if self.env["ir.module.module"]._get("account_accountant").state != "installed":
            self.skipTest("the automatic reconciliation on create comes with account_accountant")

    def import_lines(self):
        data_file = self.sheet(
            [
                ("01/10/2026", "Imp. Ley 25413 debito", "-120,50", "1.000,00"),
                ("01/10/2026", "Transferencia recibida", "500,00", "1.500,00"),
            ]
        )
        result = self.import_wizard(data_file)._import_file()
        return self.env["account.bank.statement"].browse(result["statement_ids"]).line_ids.sorted("payment_ref")

    def test_import_reconciles_by_default(self):
        """A line matched by an automatic model is reconciled by the import itself, not by the daily cron."""
        self.assertRecordValues(
            self.import_lines(),
            [
                {"payment_ref": "Imp. Ley 25413 debito", "is_reconciled": True},
                {"payment_ref": "Transferencia recibida", "is_reconciled": False},
            ],
        )

    def test_import_does_not_reconcile_when_the_company_opts_out(self):
        """With the setting off nothing is reconciled, even if the context asks for it.

        The bank matching action of account_accountant puts auto_statement_processing
        in the context, and an import opened from there inherits it.
        """
        self.env.company.statement_import_auto_reconcile = False
        self.env = self.env(context=dict(self.env.context, auto_statement_processing=True))
        self.assertRecordValues(
            self.import_lines(),
            [
                {"payment_ref": "Imp. Ley 25413 debito", "is_reconciled": False},
                {"payment_ref": "Transferencia recibida", "is_reconciled": False},
            ],
        )
