from odoo.tests.common import TransactionCase


class TestImportPreValidation(TransactionCase):
    """A single badly-formatted number/date must NOT abort the whole import:
    the raw value is kept so the per-record ORM converter reports it (with its
    row) alongside every other error, instead of raising on the first bad cell.
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

    def test_bad_date_does_not_abort_and_keeps_raw(self):
        imp = self.env["base_import.import"]
        data = [["2024-01-15"], ["not-a-date"], ["2024-02-20"]]
        imp._parse_date_from_data(data, 0, "date", "date", {})
        self.assertEqual(data[0][0], "2024-01-15")
        self.assertEqual(data[1][0], "not-a-date")  # bad value deferred, not cut
        self.assertEqual(data[2][0], "2024-02-20")
