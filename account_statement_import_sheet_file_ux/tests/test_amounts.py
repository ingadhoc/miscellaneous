from odoo.exceptions import UserError

from .common import SheetMappingCase


class TestAmounts(SheetMappingCase):
    """The amounts of a sheet, which is where a mapping corrupts data silently."""

    def _amount(self, written, mapping=None, header=("Date", "Amount")):
        mapping = mapping or self.new_mapping(description_column=False, balance_column=False)
        data_file = self.sheet([("21/08/2026", written)], header=header)
        _currency, _account, statements = self.parse(data_file, mapping)
        return float(statements[0]["transactions"][0]["amount"])

    def test_a_numeric_cell_is_not_shifted_by_the_separators(self):
        """A number in the sheet carries no separator to interpret."""
        for written in [1500.5, 1500.0, -250.75, 1500]:
            with self.subTest(written=written):
                self.assertEqual(self._amount(written), float(written))

    def test_a_declared_mark_is_accepted(self):
        for thousands, decimal, written, expected in [
            ("dot", "comma", "1.500,50", 1500.5),
            ("comma", "dot", "1,500.50", 1500.5),
            ("none", "dot", "1500.50", 1500.5),
        ]:
            with self.subTest(written=written):
                mapping = self.new_mapping(
                    description_column=False,
                    balance_column=False,
                    float_thousands_sep=thousands,
                    float_decimal_sep=decimal,
                )
                self.assertEqual(self._amount(written, mapping), expected)

    def test_an_undeclared_decimal_mark_is_refused(self):
        mapping = self.new_mapping(
            description_column=False,
            balance_column=False,
            float_thousands_sep="none",
        )
        with self.assertRaises(UserError) as catcher:
            self._amount("1500.50", mapping)
        self.assertIn("1500.50", str(catcher.exception))

    def test_the_check_is_skipped_without_a_decimal_separator(self):
        """That mode reads the last digits as the decimals, its own contract."""
        mapping = self.new_mapping(
            description_column=False,
            balance_column=False,
            float_decimal_sep="none",
        )
        self.assertEqual(self._amount("1500.50", mapping), 1500.5)
