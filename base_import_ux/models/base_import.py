import datetime

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class BaseImport(models.TransientModel):
    _inherit = "base_import.import"

    @api.model
    def _parse_float_from_data(self, data, index, name, options):
        """Do not abort the whole import on the first badly-formatted number.

        The standard method (see base_import/models/base_import.py) raises an
        ``ImportValidationError`` as soon as one cell of a float/monetary column
        cannot be parsed, which cancels the entire import and hides every other
        error (and the offending row number). Here, when a value cannot be
        parsed, we leave the original value untouched so the per-record ORM
        converter reports it with its row number, together with every other
        field/record error, in a single pass. Well-formed values are still
        pre-cleaned (currency symbols, thousands separators) exactly as before.
        """
        for line in data:
            raw = line[index] = line[index].strip()
            if not line[index]:
                continue
            thousand_separator, decimal_separator = self._infer_separators(line[index], options)

            if "E" in line[index] or "e" in line[index]:
                tmp_value = line[index].replace(thousand_separator, ".")
                try:
                    tmp_value = f"{float(tmp_value):f}"
                    line[index] = tmp_value
                    thousand_separator = " "
                except Exception:  # noqa: BLE001
                    pass

            line[index] = line[index].replace(thousand_separator, "").replace(decimal_separator, ".")
            cleaned = self._remove_currency_symbol(line[index])
            # Defer to the ORM converter instead of raising (which would cut the
            # whole import): restore the raw value so the error is reported per
            # row and accumulated with the rest.
            line[index] = cleaned if cleaned is not False else raw

    @api.model
    def _parse_date_from_data(self, data, index, name, field_type, options):
        """Same rationale as ``_parse_float_from_data`` for date/datetime columns.

        A badly-formatted date no longer cancels the whole import: the raw value
        is kept and the per-record ORM converter reports it (with its row number
        and the expected format hint) alongside every other error. Genuinely
        unexpected (non-``ValueError``) failures are still raised, as they signal
        a real problem rather than user data.
        """
        dt = datetime.datetime
        fmt = fields.Date.to_string if field_type == "date" else fields.Datetime.to_string
        d_fmt = options.get("date_format") or DEFAULT_SERVER_DATE_FORMAT
        dt_fmt = options.get("datetime_format") or DEFAULT_SERVER_DATETIME_FORMAT
        for line in data:
            if not line[index] or isinstance(line[index], datetime.date):
                continue

            raw = line[index]
            v = line[index].strip()
            try:
                # first try parsing as a datetime if it's one
                if dt_fmt and field_type == "datetime":
                    try:
                        line[index] = fmt(dt.strptime(v, dt_fmt))
                        continue
                    except ValueError:
                        pass
                # otherwise try parsing as a date whether it's a date
                # or datetime
                line[index] = fmt(dt.strptime(v, d_fmt))
            except ValueError:
                # Bad user-supplied date: keep the raw value and let the ORM
                # converter report it per row instead of cutting the import.
                line[index] = raw
