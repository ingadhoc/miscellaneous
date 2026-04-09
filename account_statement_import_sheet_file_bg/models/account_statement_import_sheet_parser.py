# Copyright 2026 ADHOC SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    @api.model
    def parse_header(self, csv_or_xlsx, mapping):
        if mapping.no_header:
            return []

        header_line = mapping.header_lines_skip_count
        # Prevent negative indexes.
        if header_line > 0:
            header_line -= 1

        if isinstance(csv_or_xlsx, tuple):
            return super().parse_header(csv_or_xlsx, mapping)

        [next(csv_or_xlsx) for _i in range(header_line)]
        header = []
        for value in next(csv_or_xlsx):
            raw_value = value.value if hasattr(value, "value") else value
            header.append(str(raw_value).strip() if raw_value is not None else "")

        if mapping.offset_column:
            header = header[mapping.offset_column :]
        return header
