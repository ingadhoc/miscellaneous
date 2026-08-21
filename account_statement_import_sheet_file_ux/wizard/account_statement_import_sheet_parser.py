import re
from datetime import datetime
from decimal import Decimal

from odoo import api, models
from odoo.exceptions import UserError

# Spanish month names, as the banks of the region write them, mapped to the
# English ones `datetime.strptime` understands for %b and %B. strptime reads
# month names in the C locale only, so '21-Ago-2026' with '%d-%b-%Y' fails
# while '21-aug-2026' works, and month names are matched case insensitively.
SPANISH_MONTHS = {
    "enero": "january",
    "febrero": "february",
    "marzo": "march",
    "abril": "april",
    "mayo": "may",
    "junio": "june",
    "julio": "july",
    "agosto": "august",
    "septiembre": "september",
    "setiembre": "september",
    "octubre": "october",
    "noviembre": "november",
    "diciembre": "december",
    "ene": "jan",
    "feb": "feb",
    "mar": "mar",
    "abr": "apr",
    "may": "may",
    "jun": "jun",
    "jul": "jul",
    "ago": "aug",
    "sep": "sep",
    "set": "sep",
    "oct": "oct",
    "nov": "nov",
    "dic": "dec",
}
# Longest first, so that "enero" is not eaten by "ene"
SPANISH_MONTHS_RE = re.compile(
    r"\b(%s)\b" % "|".join(sorted(SPANISH_MONTHS, key=len, reverse=True)),
    re.IGNORECASE,
)

# Compiled once: they run on every amount of every row of the file
NOISE_RE = re.compile(r"[^\d\-+.,]+")
DECIMAL_MARK_RE = {
    ".": re.compile(r"\.\d{1,2}$"),
    ",": re.compile(r",\d{1,2}$"),
}


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _get_column_indexes(self, header, column_name, mapping):
        """Match the configured column names ignoring case and padding.

        Banks change the capitalization of their headers between exports and the
        whole import fails on a ``'Debit' is not in list`` error.

        The exact lookup is tried first and the tolerant one only on failure, on
        purpose: a header can legitimately hold two cells that differ just in
        case, and the exact spelling has to keep winning there.
        """
        try:
            return super()._get_column_indexes(header, column_name, mapping)
        except ValueError:
            configured = {}
            for spelling in (mapping[column_name] or "").split(","):
                key = spelling.strip().lower()
                if key:
                    # the raw spelling, padding included, is what the standard
                    # lookup searches the header for
                    configured[key] = spelling
            if not configured:
                raise
            normalized = [configured.get(str(cell).strip().lower(), cell) for cell in header]
            return super()._get_column_indexes(normalized, column_name, mapping)

    def _get_values_from_column(self, values, columns, column_name):
        """Read the month names of a date column in Spanish as well as English."""
        value = super()._get_values_from_column(values, columns, column_name)
        if (
            column_name == "timestamp_column"
            and isinstance(value, str)
            # a numeric date carries no month name to translate
            and any(character.isalpha() for character in value)
        ):
            value = SPANISH_MONTHS_RE.sub(lambda match: SPANISH_MONTHS[match.group(0).lower()], value)
        return value

    def _get_xlsx_row_values(self, mapping, xlsx, rows, label_line):
        """Read the rows of an xlsx keeping the numeric cells native.

        Mirrors OCA/bank-statement-import#996. The whole method is rewritten
        because the standard one offers no hook per cell; the per-cell rule
        lives in ``_xlsx_cell_value`` so that the next one extends a hook
        instead of forking this fork again.
        """
        first_column = mapping.offset_column + 1
        # openpyxl walks every cell of the sheet to answer max_column, so it is
        # read once instead of once per row
        last_column = xlsx.max_column
        return [
            [
                self._xlsx_cell_value(mapping, xlsx.cell(row=row, column=column).value)
                for column in range(first_column, last_column + 1)
            ]
            for row in rows
        ]

    def _xlsx_cell_value(self, mapping, cell_value):
        """Return one cell of an xlsx as the parser wants to read it.

        A number is kept native: stringifying it prints python notation, a dot
        as the decimal separator, and a mapping configured with a comma then
        drops that dot and shifts the amount by a factor of ten or a hundred --
        a different factor per value, so there is no multiple to apply
        afterwards.
        """
        if cell_value is None:
            # an empty cell reads as empty text; str() would hand the parser
            # the word "None", which is truthy and lands in the statement
            return ""
        if isinstance(cell_value, datetime):
            return cell_value.strftime(mapping.timestamp_format)
        if isinstance(cell_value, bool) or not isinstance(cell_value, int | float):
            return str(cell_value)
        return cell_value

    @api.model
    def _check_decimal_mark(self, value, thousands, decimal):
        """Refuse a value whose decimal mark the mapping does not account for.

        A thousands separator always groups three digits, so a "." or a "," that
        is followed by fewer than three digits at the end of the value can only
        be a decimal mark. When it is not the configured one it gets stripped as
        noise, which multiplies the amount by ten or a hundred -- silently, and
        with no way to tell afterwards, since the factor varies per value.

        Skipped when no decimal separator is configured: that mode reads the
        last digits as the decimals, so it has a contract of its own.

        Mirrors OCA/bank-statement-import#997.
        """
        if not decimal or ("." not in value and "," not in value):
            return
        cleaned = NOISE_RE.sub("", value)
        for candidate, pattern in DECIMAL_MARK_RE.items():
            if candidate in (thousands, decimal):
                continue
            if pattern.search(cleaned):
                raise UserError(
                    self.env._(
                        "Cannot read the amount %(value)s: it uses %(candidate)s as "
                        "the decimal mark, but the statement mapping declares "
                        "%(decimal)s. Importing it would change the amount. Fix the "
                        "decimal separator of the mapping and import the file again.",
                        value=value,
                        candidate=candidate,
                        decimal=decimal,
                    )
                )

    @api.model
    def _parse_decimal(self, value, mapping):
        """Vet the decimal mark of the strings and let the numbers through.

        The type branches cannot be left to the standard method: it does not
        short-circuit ``int``, which openpyxl hands over for a whole value and
        which raises ``TypeError`` on reaching its regex.
        """
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
        if not isinstance(value, str):
            value = str(value)
        self._check_decimal_mark(value, *mapping._get_float_separators())
        return super()._parse_decimal(value, mapping)
