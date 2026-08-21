from odoo import api, fields, models


class AccountStatementImportSheetMappingTest(models.TransientModel):
    _name = "account.statement.import.sheet.mapping.test"
    _description = "Bank Statement Import Sheet Mapping Test"

    mapping_id = fields.Many2one(
        comodel_name="account.statement.import.sheet.mapping",
        string="Mapping",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        domain=[("type", "in", ("bank", "cash"))],
        default=lambda self: self._default_journal_id(),
        help="The file is read as if it were being imported in this journal, "
        "which is what decides the currency of the transactions.",
    )
    statement_file = fields.Binary(string="File", required=True)
    statement_filename = fields.Char(string="File Name")

    @api.model
    def _default_journal_id(self):
        """A bank journal that already imports with a mapping, if there is one."""
        return self.env["account.journal"].search(
            [("type", "=", "bank"), ("default_sheet_mapping_id", "!=", False)],
            limit=1,
        )

    def action_test(self):
        """Analyse the file with this mapping, creating nothing."""
        self.ensure_one()
        # a virtual record: not even the import wizard is written to the database
        return (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal_id.id)
            .new(
                {
                    "sheet_mapping_id": self.mapping_id.id,
                    "statement_file": self.statement_file,
                    "statement_filename": self.statement_filename or "statement",
                }
            )
            .action_test_import(next_action=self._reopen_test())
        )

    def _reopen_test(self):
        """Leave the user here, with the file and the journal still filled in.

        A wizard button closes its dialog, and testing a mapping is something
        one does two or three times in a row.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
            "context": dict(self.env.context),
        }
