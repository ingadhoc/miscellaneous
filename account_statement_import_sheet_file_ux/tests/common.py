from base64 import b64encode
from io import BytesIO

import xlsxwriter
from odoo.tests.common import TransactionCase

MAPPING_VALUES = {
    "name": "Test Mapping",
    "timestamp_format": "%d/%m/%Y",
    "timestamp_column": "Date",
    "description_column": "Label",
    "amount_type": "simple_value",
    "amount_column": "Amount",
    "balance_column": "Balance",
    "float_thousands_sep": "dot",
    "float_decimal_sep": "comma",
    "header_lines_skip_count": 1,
}
HEADER = ("Date", "Label", "Amount", "Balance")


class SheetMappingCase(TransactionCase):
    """The fixtures every test of this module needs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mapping = cls.env["account.statement.import.sheet.mapping"]
        cls.Preview = cls.env["account.statement.import.sheet.mapping.preview"]
        cls.parser = cls.env["account.statement.import.sheet.parser"]
        cls.mapping_values = dict(MAPPING_VALUES)
        cls.mapping = cls.Mapping.create(dict(cls.mapping_values))
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank UX",
                "type": "bank",
                "code": "BNKUX",
                "currency_id": cls.env.company.currency_id.id,
            }
        )

    def new_mapping(self, **values):
        return self.Mapping.create(dict(self.mapping_values, **values))

    def sheet(self, rows, header=HEADER):
        """An xlsx with a header row; strings are written as text, numbers as numbers."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Extracto")
        for column, title in enumerate(header):
            worksheet.write_string(0, column, title)
        for index, row in enumerate(rows, start=1):
            for column, value in enumerate(row):
                if value is None:
                    # left blank on purpose, the way a bank leaves a cell empty
                    continue
                if isinstance(value, str):
                    worksheet.write_string(index, column, value)
                else:
                    worksheet.write_number(index, column, value)
        workbook.close()
        return output.getvalue()

    def import_wizard(self, data_file=None, mapping=None):
        values = {
            "statement_filename": "statement.xlsx",
            "sheet_mapping_id": (mapping or self.mapping).id,
        }
        if data_file is not None:
            values["statement_file"] = b64encode(data_file)
        return self.env["account.statement.import"].with_context(journal_id=self.journal.id).create(values)

    def parse(self, data_file, mapping=None):
        return self.parser.with_context(journal_id=self.journal.id).parse(
            data_file, mapping or self.mapping, "statement.xlsx"
        )

    def sample_file(self, mapping=None):
        """The xlsx the preview offers for a mapping."""
        mapping = mapping or self.mapping
        return self.Preview.create({"mapping_id": mapping.id})._build_xlsx()
