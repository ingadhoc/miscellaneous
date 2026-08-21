from unittest.mock import patch

from odoo import fields

from .common import SheetMappingCase


class TestSkipPdfGeneration(SheetMappingCase):
    def _statement_values(self):
        today = fields.Date.context_today(self.mapping)
        return [
            {
                "journal_id": self.journal.id,
                "name": "Imported statement",
                "date": today,
                "transactions": [
                    {
                        "journal_id": self.journal.id,
                        "date": today,
                        "payment_ref": "Sample transaction",
                        "amount": "100.0",
                    }
                ],
            }
        ]

    def test_pdf_render_is_skipped_while_importing(self):
        """The render is what makes a large import time out."""
        wizard = self.import_wizard()
        Statement = self.env["account.bank.statement"]
        captured = {}
        original_create = type(Statement).create

        def spy(records, vals_list):
            captured["context"] = records.env.context
            return original_create(records, vals_list)

        result = {"statement_ids": []}
        stmts_vals = wizard._complete_stmts_vals(self._statement_values(), self.journal, self.journal.bank_account_id)
        with patch.object(type(Statement), "create", spy):
            wizard._create_bank_statements(stmts_vals, result)
        self.assertTrue(result["statement_ids"], "the statement was not created")
        self.assertTrue(
            captured["context"].get("skip_pdf_attachment_generation"),
            "the statement was created without the flag that skips the PDF render",
        )

    def test_the_flag_travels_on_the_documented_seam(self):
        """`creation_context` is what the base module pops and passes to create."""
        wizard = self.import_wizard()
        stmts_vals = wizard._complete_stmts_vals(self._statement_values(), self.journal, self.journal.bank_account_id)
        self.assertTrue(stmts_vals[0]["creation_context"]["skip_pdf_attachment_generation"])
