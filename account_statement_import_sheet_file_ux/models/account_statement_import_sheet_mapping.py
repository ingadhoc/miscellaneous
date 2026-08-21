import re
from datetime import timedelta

from odoo import api, fields, models
from xlsxwriter.utility import xl_col_to_name

# Signed amounts of the sample lines, as they are meant to end up in Odoo
PREVIEW_AMOUNTS = [1500.0, -2750.5, 350.75]
PREVIEW_LINES = len(PREVIEW_AMOUNTS)
PREVIEW_OPENING_BALANCE = 10000.0


class AccountStatementImportSheetMapping(models.Model):
    _inherit = "account.statement.import.sheet.mapping"

    header_lines_skip_count = fields.Integer(
        string="Header row number",
        help="Row number where the column headers are located, the first row "
        "being 1. Use the 'Preview Mapping' button to check how the file is "
        "expected to look with the current configuration.",
    )
    timestamp_format = fields.Char(
        help="How the dates are written in the file: %d day, %m month as a "
        "number, %b month in three letters, %B full month name, %Y year in "
        "four digits, %y year in two digits. For example 25/12/2026 is "
        "%d/%m/%Y. Use the 'Preview Mapping' button to see it decoded.",
    )
    amount_type = fields.Selection(
        help="Simple value: use the signed amount in the amount column\n"
        "Absolute value: use a same column for debit and credit "
        "(absolute value + indicate sign)\n"
        "Distinct Credit/debit Column: use a distinct column for debit and credit",
    )

    @api.onchange("amount_type")
    def _ux_clear_amount_columns(self):
        """The columns of the previous amount type no longer apply.

        Deliberately not named after the method of the base module: an equally
        named onchange would replace it instead of running next to it, and the
        replacement would be invisible in the code.
        """
        self.amount_column = False
        self.debit_credit_column = False
        self.amount_debit_column = False
        self.amount_credit_column = False

    def action_preview_mapping(self):
        """Open a sample of the file this mapping expects."""
        self.ensure_one()
        preview = self.env["account.statement.import.sheet.mapping.preview"].create({"mapping_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Mapping preview"),
            "res_model": preview._name,
            "res_id": preview.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_test_import_file(self):
        """Ask for a file and run the import analysis on it, creating nothing."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Test import"),
            "res_model": "account.statement.import.sheet.mapping.test",
            "view_mode": "form",
            "target": "new",
            "context": {"default_mapping_id": self.id},
        }

    # Preview building blocks

    def _preview_column_field_names(self):
        """Mapping fields that may define a column, in the order they are laid out.

        The set comes from the parser, which is what actually reads them, so a
        column field added by another module shows up in the preview and in the
        sample file instead of being parsed but never drawn.
        """
        self.ensure_one()
        parser = self.env["account.statement.import.sheet.parser"]
        known = parser._get_column_names()
        names = [
            "timestamp_column",
            "transaction_id_column",
            "reference_column",
            "partner_name_column",
            "description_column",
            "notes_column",
        ]
        if self.amount_type == "distinct_credit_debit":
            names += ["amount_debit_column", "amount_credit_column"]
        else:
            names += ["amount_column"]
            if self.amount_type == "absolute_value":
                names += ["debit_credit_column"]
        names += [
            "balance_column",
            "currency_column",
            "original_currency_column",
            "original_amount_column",
            "bank_name_column",
            "bank_account_column",
        ]
        # every other column the parser reads, because it demands each one of
        # them to exist in the file whether the amount type uses it or not
        return [name for name in names if name in known] + [name for name in known if name not in names]

    def _preview_column_keys(self, field_name):
        """Column names (or indexes) configured on a mapping field."""
        self.ensure_one()
        return [key.strip() for key in (self[field_name] or "").split(",") if key.strip()]

    @api.model
    def _preview_column_index(self, key):
        """The column index a mapping key holds, or None when it is a name."""
        try:
            return int(key)
        except ValueError:
            return None

    def _preview_format_date(self, date):
        self.ensure_one()
        try:
            return date.strftime(self.timestamp_format)
        except (ValueError, TypeError):
            return date.isoformat()

    def _preview_format_amount(self, amount):
        self.ensure_one()
        thousands, decimal = self._get_float_separators()
        if not decimal:
            # Without a decimal separator the parser shifts the value according
            # to the currency decimals, so the file must hold plain digits
            return str(round(amount * 10 ** self._preview_decimal_places()))
        # One pass, so that both separators can be configured to the same
        # character without the swap clashing with itself
        return f"{amount:,.2f}".translate(str.maketrans({",": thousands, ".": decimal}))

    def _preview_currency(self):
        """The currency the parser will compare the sample against.

        A line whose currency column does not match the currency of the journal
        being imported into is dropped, so the sample has to carry that one.
        """
        self.ensure_one()
        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))
        return journal.currency_id or self.env.company.currency_id

    def _preview_decimal_places(self):
        """The decimals the parser shifts by when no separator is configured."""
        self.ensure_one()
        return self._preview_currency().decimal_places

    def _preview_sample_values(self):
        """Return {mapping field: one already formatted value per sample line}."""
        self.ensure_one()
        # The file holds the inverse sign when the mapping inverts it on import
        amounts = [-amount if self.amount_inverse_sign else amount for amount in PREVIEW_AMOUNTS]
        balance = PREVIEW_OPENING_BALANCE
        balances = []
        for amount in amounts:
            balance += amount
            balances.append(balance)
        today = fields.Date.context_today(self)
        dates = [today - timedelta(days=days) for days in reversed(range(PREVIEW_LINES))]
        currency = self._preview_currency()
        values = {
            "timestamp_column": [self._preview_format_date(date) for date in dates],
            "transaction_id_column": ["000123", "000124", "000125"],
            "reference_column": ["REF-0001", "REF-0002", "REF-0003"],
            "partner_name_column": [
                self.env._("Customer A"),
                self.env._("Supplier B"),
                self.env._("Sample Bank"),
            ],
            "description_column": [
                self.env._("Incoming transfer"),
                self.env._("Supplier payment"),
                self.env._("Bank fee"),
            ],
            "notes_column": [self.env._("Sample line")] * PREVIEW_LINES,
            "balance_column": [self._preview_format_amount(balance) for balance in balances],
            "currency_column": [currency.name] * PREVIEW_LINES,
            "original_currency_column": ["EUR" if currency.name == "USD" else "USD"] * PREVIEW_LINES,
            "original_amount_column": [self._preview_format_amount(abs(amount) / 1000) for amount in amounts],
            "bank_name_column": [self.env._("Sample Bank")] * PREVIEW_LINES,
            "bank_account_column": ["0000076500000000000001"] * PREVIEW_LINES,
        }
        if self.amount_type == "distinct_credit_debit":
            values["amount_debit_column"] = [
                self._preview_format_amount(amount) if amount > 0 else "" for amount in amounts
            ]
            values["amount_credit_column"] = [
                self._preview_format_amount(-amount) if amount < 0 else "" for amount in amounts
            ]
        elif self.amount_type == "absolute_value":
            values["amount_column"] = [self._preview_format_amount(abs(amount)) for amount in amounts]
            values["debit_credit_column"] = [
                self.debit_value if amount < 0 else self.credit_value for amount in amounts
            ]
        else:
            values["amount_column"] = [self._preview_format_amount(amount) for amount in amounts]
        return values

    @api.model
    def _preview_split_value(self, value, count):
        """Spread a sample value over the columns a mapping field concatenates."""
        words = value.split(" ")
        if len(words) < count:
            return [value] + [""] * (count - 1)
        return words[: count - 1] + [" ".join(words[count - 1 :])]

    def _preview_columns(self):
        """Return the sample columns as {0-based index: (label, [value per line])}.

        Without a header the mapping holds column indexes, so each field lands on
        the position it declares. With a header the file order is irrelevant to
        the parser, so the columns are laid out in the order of the form.
        """
        self.ensure_one()
        sample_values = self._preview_sample_values()
        columns = {}
        position = 0 if self.no_header else self.offset_column
        for field_name in self._preview_column_field_names():
            keys = self._preview_column_keys(field_name)
            if not keys:
                continue
            # a field with no sample value of its own still gets its columns
            values = sample_values.get(field_name, [""] * PREVIEW_LINES)
            splits = [self._preview_split_value(value, len(keys)) for value in values]
            for offset, key in enumerate(keys):
                if self.no_header:
                    index = self._preview_column_index(key)
                    if index is not None:
                        # the parser reads each row from offset_column on, so a
                        # mapping index counts from there, not from column A
                        index += self.offset_column
                    else:
                        # the mapping is misconfigured; the preview reports
                        # it as a warning instead of failing here
                        continue
                else:
                    index = position
                    position += 1
                columns[index] = (key, [split[offset] for split in splits])
        return columns

    def _preview_layout(self):
        """The sample sheet plus everything that explains it."""
        self.ensure_one()
        return {
            **self._preview_grid(),
            "dates": self._preview_date_help(),
            "notes": self._preview_notes(),
            "warnings": self._preview_warnings(),
        }

    def _preview_grid(self):
        """Return just the sample sheet, which is all the export needs.

        The layout follows what the parser actually does with the mapping: the
        header sits on ``max(header_lines_skip_count, 1)`` and the transactions
        start right after ``header_lines_skip_count``.
        """
        self.ensure_one()
        columns = self._preview_columns()
        width = max(columns) + 1 if columns else 0
        header_row = None if self.no_header else max(self.header_lines_skip_count, 1)
        first_data_row = self.header_lines_skip_count + 1 if self.no_header else header_row + 1
        # Ignored rows carry a label so that they exist in the exported file:
        # a fully empty row would not be there and the row numbers would shift
        ignored_cells = [self.env._("Ignored row")] + [""] * (width - 1) if width else []
        rows = []
        for number in range(1, first_data_row):
            if number == header_row:
                cells = [columns[index][0] if index in columns else "" for index in range(width)]
            else:
                cells = list(ignored_cells)
            rows.append(
                {
                    "number": number,
                    "kind": "header" if number == header_row else "ignored",
                    "cells": cells,
                }
            )
        for line in range(PREVIEW_LINES):
            rows.append(
                {
                    "number": first_data_row + line,
                    "kind": "data",
                    "cells": [columns[index][1][line] if index in columns else "" for index in range(width)],
                }
            )
        for footer in range(self.footer_lines_skip_count):
            rows.append(
                {
                    "number": first_data_row + PREVIEW_LINES + footer,
                    "kind": "ignored",
                    "cells": list(ignored_cells),
                }
            )
        return {
            "letters": [xl_col_to_name(index) for index in range(width)],
            "rows": rows,
        }

    def _preview_date_codes(self):
        """The strftime codes a mapping can use, in one place.

        ``word`` decodes the format into a sentence and ``label`` plus
        ``example`` build the legend; a code with no label is decoded but not
        listed, because a statement rarely carries the time of day.

        The labels are resolved before being paired with the codes: a
        translatable call next to a literal holding a % confuses the exporter
        into emitting the literal as a term of its own.
        """
        self.ensure_one()
        day = self.env._("day")
        month = self.env._("month")
        year = self.env._("year")
        hour = self.env._("hour")
        minute = self.env._("minute")
        second = self.env._("second")
        day_label = self.env._("day of the month")
        month_number_label = self.env._("month as a number")
        month_short_label = self.env._("month in three letters")
        month_long_label = self.env._("full month name")
        year_short_label = self.env._("year in two digits")
        year_long_label = self.env._("year in four digits")
        return [
            ("%d", day, day_label, "01, 02, ... 31"),
            ("%m", month, month_number_label, "01, 02, ... 12"),
            ("%b", month, month_short_label, "Ago, Aug"),
            ("%B", month, month_long_label, "Agosto, August"),
            ("%y", year, year_short_label, "26"),
            ("%Y", year, year_long_label, "2026"),
            ("%H", hour, None, None),
            ("%M", minute, None, None),
            ("%S", second, None, None),
        ]

    def _preview_date_help(self):
        """Read the date format back to the user, code by code.

        The format is the single hardest field of the mapping to get right, and
        the failure it produces (a date that does not parse) says nothing about
        which code is wrong.
        """
        self.ensure_one()
        fmt = self.timestamp_format or ""
        return {
            "sentence": self.env._(
                "The dates are read with %(format)s, that is %(decoded)s.",
                format=fmt,
                decoded=self._preview_decoded_date_format(),
            ),
            "codes": [
                {"code": code, "label": label, "example": example, "used": code in fmt}
                for code, _word, label, example in self._preview_date_codes()
                if label
            ],
            "month_in_letters": bool(re.search(r"%[bB]", fmt)),
            "format": fmt,
        }

    def _preview_decoded_date_format(self):
        """Spell the date format out, so '%d/%m/%Y' reads as 'day/month/year'."""
        self.ensure_one()
        words = {code: word for code, word, _label, _example in self._preview_date_codes()}
        return re.sub(
            r"%[a-zA-Z]",
            lambda match: words.get(match.group(0), match.group(0)),
            self.timestamp_format or "",
        )

    def _preview_notes(self):
        """Read this mapping back to the user in plain words."""
        self.ensure_one()
        thousands, decimal = self._get_float_separators()
        notes = []
        if self.no_header:
            notes.append(
                self.env._(
                    "The file must have no header row: the mapping points at "
                    "column positions, so the order shown here is the one your "
                    "file needs."
                )
            )
        else:
            notes.append(
                self.env._(
                    "The order of the columns in your file does not matter and "
                    "extra columns are ignored: only the header names have to "
                    "match the ones shown here."
                )
            )
        if not decimal:
            notes.append(
                self.env._(
                    "Amounts carry no separator at all: the last %s digits are " "read as the decimals.",
                    self._preview_decimal_places(),
                )
            )
        elif thousands:
            notes.append(
                self.env._(
                    "Amounts use '%(thousands)s' as thousands separator and " "'%(decimal)s' as decimal separator.",
                    thousands=thousands,
                    decimal=decimal,
                )
            )
        else:
            notes.append(
                self.env._(
                    "Amounts use '%s' as decimal separator and no thousands " "separator.",
                    decimal,
                )
            )
        if self.offset_column:
            notes.append(
                self.env._(
                    "Columns ignored at the beginning of each row: %s.",
                    self.offset_column,
                )
            )
        if self.footer_lines_skip_count:
            notes.append(
                self.env._(
                    "Rows ignored at the end of the file: %s.",
                    self.footer_lines_skip_count,
                )
            )
        notes.append(
            self.env._(
                "The sample file can be imported as is: use it to check the "
                "mapping before fighting with the real statement."
            )
        )
        return notes

    def _amount_columns_in_use(self):
        """The amount columns the configured amount type actually reads."""
        self.ensure_one()
        if self.amount_type == "distinct_credit_debit":
            return {"amount_debit_column", "amount_credit_column"}
        if self.amount_type == "absolute_value":
            return {"amount_column", "debit_credit_column"}
        return {"amount_column"}

    def _preview_warnings(self):
        """Configuration that is going to break the import, spelled out."""
        self.ensure_one()
        warnings = []
        if not self.no_header and not self.header_lines_skip_count:
            warnings.append(
                self.env._(
                    "The header row number is 0. When importing a spreadsheet "
                    "the header row is then read as a transaction too and the "
                    "import fails. Set it to 1 if the headers are in the first "
                    "row of the file."
                )
            )
        unused = [
            field_name
            for field_name in (
                "amount_column",
                "debit_credit_column",
                "amount_debit_column",
                "amount_credit_column",
            )
            if self[field_name] and field_name not in self._amount_columns_in_use()
        ]
        if unused:
            warnings.append(
                self.env._(
                    "The amount type does not read these columns, but the "
                    "mapping still demands that the file contain them, and an "
                    "empty one corrupts the amount: %s. Clear them, or change "
                    "the amount type.",
                    ", ".join(self._fields[field_name].get_description(self.env)["string"] for field_name in unused),
                )
            )
        if self.no_header and self.header_lines_skip_count:
            warnings.append(
                self.env._(
                    "The file has no header line, so its first rows are "
                    "transactions -- and this configuration skips %s of them. "
                    "Set the header row number to 0 when there is no header.",
                    self.header_lines_skip_count,
                )
            )
        if self.no_header:
            missing = [
                field_name
                for field_name in self._preview_column_field_names()
                if any(self._preview_column_index(key) is None for key in self._preview_column_keys(field_name))
            ]
            if missing:
                warnings.append(
                    self.env._(
                        "The file has no header line, so every column has to be "
                        "a number (the first column is 0). These fields hold a "
                        "name instead and are not shown below: %s",
                        ", ".join(
                            self._fields[field_name].get_description(self.env)["string"] for field_name in missing
                        ),
                    )
                )
        return warnings
