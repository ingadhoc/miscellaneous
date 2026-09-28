from odoo.tools import file_open
from odoo.tools.mimetypes import guess_mimetype

from .common import SheetMappingCase


class TestSheetType(SheetMappingCase):
    """Which files are read as xls."""

    def test_an_xls_without_the_excel_marker_is_read(self):
        """The xls that bank systems generate do not always say 'Microsoft Excel'."""
        with file_open(
            "account_statement_import_sheet_file_ux/tests/data/statement_without_excel_marker.xls", "rb"
        ) as f:
            data_file = f.read()
        # the case only holds while the guess misses this file
        self.assertNotEqual(guess_mimetype(data_file), "application/vnd.ms-excel")
        _currency, _account, statements = self.parse(data_file)
        transactions = statements[0]["transactions"]
        self.assertEqual([float(t["amount"]) for t in transactions], [100.0, -15.5])
        self.assertEqual(transactions[0]["date"].strftime("%Y-%m-%d"), "2026-08-01")

    def test_an_ole_file_that_is_not_a_workbook_is_still_refused(self):
        data_file = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 1024
        with self.assertRaisesRegex(ValueError, "Unsupported sheet type"):
            self.parse(data_file)
