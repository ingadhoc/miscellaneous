from odoo.addons.base_import.models.base_import import ImportValidationError
from odoo.tests.common import TransactionCase


class TestImportPreValidation(TransactionCase):
    """A single badly-formatted number/date must NOT abort the whole import:
    the raw value is kept so the per-record ORM converter reports it (with its
    row) alongside every other error, instead of raising on the first bad cell.
    Values the converter would accept but the standard rejects (nan, inf, 1_000)
    and unexpected date failures still abort it, as in the standard.
    """

    def test_bad_float_does_not_abort_and_keeps_raw(self):
        imp = self.env["base_import.import"]
        data = [["100"], ["abc"], ["1.234,56"]]
        # Must not raise (standard behaviour raised ImportValidationError here).
        imp._parse_float_from_data(data, 0, "list_price", {})
        self.assertEqual(data[0][0], "100")  # good value cleaned
        self.assertEqual(data[1][0], "abc")  # bad value deferred to the ORM
        # good value with thousands/decimal separators still normalised
        self.assertEqual(data[2][0], "1234.56")

    def test_float_values_rejected_by_standard_are_not_stored(self):
        imp = self.env["base_import.import"]
        # Python's float() accepts these, so deferring them to the ORM would store them.
        for value in ("nan", "inf", "Infinity", "1_000"):
            with self.subTest(value=value), self.assertRaises(ImportValidationError):
                imp._parse_float_from_data([["100"], [value]], 0, "list_price", {})

    def test_bad_date_does_not_abort_and_keeps_raw(self):
        imp = self.env["base_import.import"]
        data = [["2024-01-15"], ["not-a-date"], ["2024-02-20"]]
        imp._parse_date_from_data(data, 0, "date", "date", {})
        self.assertEqual(data[0][0], "2024-01-15")
        self.assertEqual(data[1][0], "not-a-date")  # bad value deferred, not cut
        self.assertEqual(data[2][0], "2024-02-20")

    def test_unexpected_date_failure_is_wrapped_like_standard(self):
        imp = self.env["base_import.import"]
        # A non-string format makes strptime raise TypeError, not ValueError.
        with self.assertRaises(ImportValidationError):
            imp._parse_date_from_data([["2024-01-15"]], 0, "date", "date", {"date_format": 123})

    def test_import_reports_every_bad_cell_with_its_row(self):
        currency = self.env.company.currency_id.name
        rows = [
            ("2001-01-01", "1.5"),
            ("not-a-date", "2.5"),
            ("2001-01-03", "abc"),
        ]
        content = "currency_id,name,rate\n" + "".join(f"{currency},{date},{rate}\n" for date, rate in rows)
        importer = self.env["base_import.import"].create(
            {
                "res_model": "res.currency.rate",
                "file": content.encode(),
                "file_type": "text/csv",
                "file_name": "rates.csv",
            }
        )
        rates_before = self.env["res.currency.rate"].search_count([])
        result = importer.execute_import(
            ["currency_id", "name", "rate"],
            ["currency_id", "name", "rate"],
            {
                "quoting": '"',
                "separator": ",",
                "has_headers": True,
                "date_format": "%Y-%m-%d",
                "float_thousand_separator": ",",
                "float_decimal_separator": ".",
            },
            dryrun=True,
        )
        errors = [message for message in result["messages"] if message["type"] == "error"]
        self.assertEqual({(error["record"], error["field"]) for error in errors}, {(1, "name"), (2, "rate")})
        self.assertEqual(self.env["res.currency.rate"].search_count([]), rates_before)
