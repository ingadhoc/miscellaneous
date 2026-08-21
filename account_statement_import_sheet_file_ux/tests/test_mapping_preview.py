from odoo.addons.account_statement_import_sheet_file_ux.models import (
    account_statement_import_sheet_mapping as mapping_module,
)
from odoo.addons.account_statement_import_sheet_file_ux.wizard.account_statement_import import (
    SheetMappingError,
)
from odoo.exceptions import RedirectWarning, UserError

from .common import SheetMappingCase


class TestMappingPreview(SheetMappingCase):
    def _layout(self, **values):
        return self.new_mapping(**values)._preview_layout()

    def _rows(self, layout, kind):
        return [row for row in layout["rows"] if row["kind"] == kind]

    # Layout

    def test_header_row_follows_the_configured_row_number(self):
        """The header lands where the parser looks for it, not one row off."""
        for row_number, expected in [(0, 1), (1, 1), (2, 2), (5, 5)]:
            with self.subTest(header_lines_skip_count=row_number):
                layout = self._layout(header_lines_skip_count=row_number)
                header_rows = self._rows(layout, "header")
                self.assertEqual(len(header_rows), 1)
                self.assertEqual(header_rows[0]["number"], expected)
                self.assertEqual(self._rows(layout, "data")[0]["number"], expected + 1)

    def test_header_row_zero_is_warned_about(self):
        """0 makes the spreadsheet parser read the header as a transaction."""
        self.assertTrue(self._layout(header_lines_skip_count=0)["warnings"])
        self.assertFalse(self._layout(header_lines_skip_count=1)["warnings"])

    def test_skipping_rows_without_a_header_is_warned_about(self):
        """Without a header the first rows are transactions, not headers."""
        indexed = dict(
            no_header=True,
            timestamp_column="0",
            description_column="1",
            amount_column="2",
            balance_column="3",
        )
        layout = self._layout(header_lines_skip_count=0, **indexed)
        self.assertFalse(layout["warnings"])
        layout = self._layout(header_lines_skip_count=1, **indexed)
        self.assertTrue(any("first rows are" in warning for warning in layout["warnings"]))

    def test_amount_columns_the_type_does_not_use_are_warned_about(self):
        """The parser demands every configured column, used or not.

        So a mapping that kept the columns of another amount type is broken for
        any file, and the preview has to say so rather than draw around it.
        """
        mapping = self.new_mapping(
            amount_type="absolute_value",
            debit_credit_column="D/C",
            debit_value="D",
            credit_value="C",
            amount_debit_column="Debit",
            amount_credit_column="Credit",
        )
        self.assertTrue(any("does not read these columns" in warning for warning in mapping._preview_warnings()))
        # and they are still drawn, because the file has to contain them
        header = self._rows(mapping._preview_layout(), "header")[0]
        self.assertIn("Debit", header["cells"])
        self.assertIn("Credit", header["cells"])

    def test_a_clean_mapping_has_no_unused_amount_column(self):
        self.assertFalse(any("does not read these columns" in warning for warning in self.mapping._preview_warnings()))

    def test_offset_columns_count_without_a_header_too(self):
        """The parser reads each row from offset_column on, header or not."""
        layout = self._layout(
            no_header=True,
            timestamp_column="0",
            description_column="1",
            amount_column="2",
            balance_column="3",
            header_lines_skip_count=0,
            offset_column=2,
        )
        first = self._rows(layout, "data")[0]
        self.assertEqual(first["cells"][0], "")
        self.assertEqual(first["cells"][1], "")
        self.assertTrue(first["cells"][2])

    def test_columns_are_offset_and_footer_rows_are_ignored(self):
        layout = self._layout(offset_column=2, footer_lines_skip_count=2)
        self.assertEqual(layout["letters"][:3], ["A", "B", "C"])
        header = self._rows(layout, "header")[0]
        self.assertEqual(header["cells"][:3], ["", "", "Date"])
        self.assertEqual(len(self._rows(layout, "ignored")), 2)

    def test_sample_lines_are_the_configured_amount_type(self):
        data = self._rows(self._layout(), "data")
        self.assertEqual([row["cells"][2] for row in data], ["1.500,00", "-2.750,50", "350,75"])
        data = self._rows(
            self._layout(
                amount_type="absolute_value",
                debit_credit_column="D/C",
                debit_value="D",
                credit_value="C",
            ),
            "data",
        )
        self.assertEqual([row["cells"][2] for row in data], ["1.500,00", "2.750,50", "350,75"])
        self.assertEqual([row["cells"][3] for row in data], ["C", "D", "C"])
        data = self._rows(
            self._layout(
                amount_type="distinct_credit_debit",
                amount_column=False,
                amount_debit_column="Debit",
                amount_credit_column="Credit",
            ),
            "data",
        )
        self.assertEqual([row["cells"][2] for row in data], ["1.500,00", "", "350,75"])
        self.assertEqual([row["cells"][3] for row in data], ["", "2.750,50", ""])

    def test_no_header_places_columns_on_their_index(self):
        layout = self._layout(
            no_header=True,
            timestamp_column="0",
            description_column="2",
            amount_column="3",
            balance_column="5",
        )
        self.assertEqual(len(layout["letters"]), 6)
        first = self._rows(layout, "data")[0]
        self.assertEqual(first["cells"][1], "")
        self.assertEqual(first["cells"][3], "1.500,00")
        self.assertFalse(self._rows(layout, "header"))

    def test_no_header_with_column_names_is_warned_about(self):
        layout = self._layout(no_header=True)
        self.assertTrue(layout["warnings"])
        self.assertFalse(layout["letters"])

    def test_concatenated_columns_get_one_column_each(self):
        layout = self._layout(description_column="Label,Detail")
        header = self._rows(layout, "header")[0]
        self.assertEqual(header["cells"][1:3], ["Label", "Detail"])
        first = self._rows(layout, "data")[0]
        self.assertTrue(first["cells"][1])
        self.assertTrue(first["cells"][2])

    def test_amounts_without_decimal_separator_are_shifted(self):
        amounts = [row["cells"][2] for row in self._rows(self._layout(float_decimal_sep="none"), "data")]
        self.assertEqual(amounts, ["150000", "-275050", "35075"])

    def test_inverse_sign_is_reflected_in_the_file(self):
        amounts = [row["cells"][2] for row in self._rows(self._layout(amount_inverse_sign=True), "data")]
        self.assertEqual(amounts, ["-1.500,00", "2.750,50", "-350,75"])

    def test_every_column_the_parser_reads_can_be_previewed(self):
        """A column field the parser knows must not be missing from the sample."""
        previewable = set(self.mapping._preview_column_field_names())
        parsed = set(self.parser._get_column_names())
        self.assertFalse(parsed - previewable)

    # Wizard

    def test_preview_renders_a_table_and_an_xlsx(self):
        preview = self.Preview.create({"mapping_id": self.mapping.id})
        self.assertIn("<table", preview.preview_html)
        self.assertIn("Date", preview.preview_html)
        self.assertTrue(preview._build_xlsx().startswith(b"PK"))
        action = preview.action_download_xlsx()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertTrue(preview.file_data)
        self.assertIn("Test+Mapping.xlsx", action["url"])

    def test_sample_file_can_be_imported_with_its_own_mapping(self):
        """The preview promises the sample is importable, so it has to be."""
        for values in [
            {},
            {"header_lines_skip_count": 3, "footer_lines_skip_count": 1},
            {
                "amount_type": "absolute_value",
                "debit_credit_column": "D/C",
                "debit_value": "D",
                "credit_value": "C",
            },
            {
                "amount_type": "distinct_credit_debit",
                "amount_column": False,
                "amount_debit_column": "Debit",
                "amount_credit_column": "Credit",
            },
        ]:
            with self.subTest(**values):
                mapping = self.new_mapping(**values)
                _currency, _account, statements = self.parse(self.sample_file(mapping), mapping)
                amounts = [float(transaction["amount"]) for transaction in statements[0]["transactions"]]
                self.assertEqual(amounts, mapping_module.PREVIEW_AMOUNTS)

    # Parser fixes

    def test_column_names_match_ignoring_case_and_spaces(self):
        for header in [["Date"], ["date"], ["DATE"], [" Date "]]:
            with self.subTest(header=header):
                self.assertEqual(
                    self.parser._get_column_indexes(header, "timestamp_column", self.mapping),
                    [0],
                )

    def test_padding_around_the_configured_name_is_tolerated(self):
        """A mapping written as "Date , Label" has to find both columns."""
        mapping = self.new_mapping(description_column="Date , Label")
        self.assertEqual(
            self.parser._get_column_indexes(["Date", "Label"], "description_column", mapping),
            [0, 1],
        )

    def test_unknown_column_still_raises(self):
        with self.assertRaises(ValueError):
            self.parser._get_column_indexes(["Fecha"], "timestamp_column", self.mapping)

    # Failed imports

    def test_a_failure_stays_a_user_error_for_the_callers(self):
        """RedirectWarning is not a UserError: it cannot be raised down here."""
        data_file = self.sample_file()
        mapping = self.new_mapping(name="Galicia", timestamp_column="Fecha")
        wizard = self.import_wizard(data_file, mapping)
        with self.assertRaises(UserError) as catcher:
            wizard._parse_file(data_file)
        message = str(catcher.exception)
        self.assertIn("expects a column named 'Fecha'", message)
        self.assertIn("Galicia", message)
        # the hint comes first, the raw parser error last
        self.assertLess(message.index("expects a column named"), message.index("Technical detail"))

    def test_the_error_of_the_button_offers_the_preview(self):
        """Carli's ask: from the error, one click into the preview."""
        data_file = self.sample_file()
        mapping = self.new_mapping(name="Galicia", timestamp_column="Fecha")
        wizard = self.import_wizard(data_file, mapping)
        with self.assertRaises(RedirectWarning) as catcher:
            wizard.import_file_button()
        _message, action, button, context = catcher.exception.args[:4]
        self.assertEqual(
            action,
            self.env.ref("account_statement_import_sheet_file_ux" ".action_preview_mapping_from_error").id,
        )
        self.assertEqual(context, {"preview_mapping_id": mapping.id})
        self.assertTrue(button)
        opened = self.env["ir.actions.server"].browse(action).with_context(**context).run()
        self.assertEqual(opened["res_model"], "account.statement.import.sheet.mapping.preview")
        self.assertEqual(self.env[opened["res_model"]].browse(opened["res_id"]).mapping_id, mapping)

    def test_a_failure_wrapped_by_another_module_still_offers_the_preview(self):
        """`..._bg` splits the file before `_parse_file`, calls the parser
        itself and re-raises whatever went wrong as a plain UserError."""
        wizard = self.import_wizard(mapping=self.new_mapping(name="Galicia"))
        with self.assertRaises(RedirectWarning) as catcher:
            with wizard._offer_the_preview():
                raise UserError("Error importing bank statement: 'Fecha' is not in list")
        message = catcher.exception.args[0]
        self.assertIn("expects a column named 'Fecha'", message)
        self.assertIn("Galicia", message)

    def test_an_unrelated_failure_is_left_alone(self):
        """Not every failure of an import is the mapping's fault."""
        wizard = self.import_wizard()
        with self.assertRaises(UserError) as catcher:
            with wizard._offer_the_preview():
                raise UserError("You have already imported this file")
        self.assertNotIsInstance(catcher.exception, RedirectWarning)

    def test_wrong_date_format_error_names_the_format(self):
        data_file = self.sample_file()
        mapping = self.new_mapping(timestamp_format="%Y-%m-%d")
        wizard = self.import_wizard(data_file, mapping)
        with self.assertRaises(SheetMappingError) as catcher:
            wizard._parse_file(data_file)
        message = str(catcher.exception)
        self.assertIn("%Y-%m-%d", message)
        self.assertIn("Timestamp format", message)

    def test_an_amount_that_cannot_be_read_explains_itself(self):
        """Our own message is the hint: it must not be demoted behind a generic one."""
        mapping = self.new_mapping(float_thousands_sep="none")
        data_file = self.sheet([("21/08/2026", "Pago", "1500.50", "1500.50")])
        wizard = self.import_wizard(data_file, mapping)
        with self.assertRaises(SheetMappingError) as catcher:
            wizard._parse_file(data_file)
        message = str(catcher.exception)
        self.assertIn("Cannot read the amount", message)
        self.assertNotIn("Technical detail", message)

    def test_import_without_mapping_is_left_alone(self):
        wizard = (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal.id)
            .create({"statement_filename": "sample.txt"})
        )
        with self.assertRaises(Exception) as catcher:
            wizard._parse_file(b"not a statement at all")
        self.assertNotIsInstance(catcher.exception, SheetMappingError)

    # The view the module has to inherit

    def test_the_inherited_form_view_is_still_the_misnamed_one(self):
        """The base module has the ids of its form and its list swapped.

        The module inherits the one named after a list; the day that is fixed
        upstream this fails here instead of at a customer.
        """
        self.assertEqual(
            self.env.ref("account_statement_import_sheet_file" ".account_statement_import_sheet_mapping_tree").type,
            "form",
        )
