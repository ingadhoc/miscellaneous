from odoo.exceptions import RedirectWarning

from .common import SheetMappingCase


class TestImportFeedback(SheetMappingCase):
    """What the user is told when an import works, and when it does not."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.letters_mapping = cls.Mapping.create(dict(cls.mapping_values, name="Galicia", timestamp_format="%d-%b-%Y"))

    # Month names in Spanish

    def test_month_names_are_read_in_spanish_too(self):
        """A file with '21-Ago-2026' has to parse, not only '21-Aug-2026'."""
        for written, expected, fmt in [
            ("21-Ago-2026", "2026-08-21", "%d-%b-%Y"),
            ("21-AGO-2026", "2026-08-21", "%d-%b-%Y"),
            ("01-Set-2026", "2026-09-01", "%d-%b-%Y"),
            ("15-Ene-2026", "2026-01-15", "%d-%b-%Y"),
            ("21-Aug-2026", "2026-08-21", "%d-%b-%Y"),
            ("21 de agosto de 2026", "2026-08-21", "%d de %B de %Y"),
        ]:
            with self.subTest(written=written):
                mapping = self.new_mapping(timestamp_format=fmt)
                data_file = self.sheet([(written, "Pago", "1.500,00", "1.500,00")])
                _currency, _account, statements = self.parse(data_file, mapping)
                self.assertEqual(
                    statements[0]["transactions"][0]["date"].strftime("%Y-%m-%d"),
                    expected,
                )

    # The date format, read back

    def test_the_date_format_is_decoded_in_words(self):
        for fmt, decoded in [
            ("%d/%m/%Y", "day/month/year"),
            ("%d-%b-%Y", "day-month-year"),
            ("%Y%m%d", "yearmonthday"),
            ("%d/%m/%Y %H:%M", "day/month/year hour:minute"),
        ]:
            with self.subTest(fmt=fmt):
                mapping = self.new_mapping(timestamp_format=fmt)
                self.assertEqual(mapping._preview_decoded_date_format(), decoded)

    def test_the_codes_used_by_the_mapping_are_flagged(self):
        help_ = self.letters_mapping._preview_date_help()
        used = [code["code"] for code in help_["codes"] if code["used"]]
        self.assertEqual(used, ["%d", "%b", "%Y"])
        self.assertTrue(help_["month_in_letters"])
        # the legend lists the codes a date needs, not the ones a time needs
        self.assertNotIn("%H", [code["code"] for code in help_["codes"]])
        self.assertFalse(self.mapping._preview_date_help()["month_in_letters"])

    # The test import

    def test_a_test_import_creates_nothing(self):
        """The whole point: it reports, and the database is left alone."""
        data_file = self.sheet(
            [
                ("21/08/2026", "Pago", "1.500,00", "1.500,00"),
                ("22/08/2026", "Cobro", "-250,50", "1.249,50"),
            ]
        )
        wizard = self.import_wizard(data_file)
        statements = self.env["account.bank.statement"].search_count([])
        lines = self.env["account.bank.statement.line"].search_count([])
        source = self.journal.bank_statements_source
        action = wizard.action_test_import()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "success")
        self.assertIn("2", action["params"]["message"])
        # the wizard comes back with the file still loaded: a wizard button
        # closes its dialog, and picking the file again is the whole complaint
        following = action["params"]["next"]
        self.assertEqual(following["res_model"], wizard._name)
        self.assertEqual(following["res_id"], wizard.id)
        self.assertTrue(wizard.statement_file)
        self.assertEqual(self.env["account.bank.statement"].search_count([]), statements)
        self.assertEqual(self.env["account.bank.statement.line"].search_count([]), lines)
        # the real import writes this on the journal; a test must not
        self.assertEqual(self.journal.bank_statements_source, source)

    def test_the_reported_dates_are_the_ones_the_import_stores(self):
        """format_date reads a naive datetime as UTC and would shift the day."""
        data_file = self.sheet([("21/08/2026", "Pago", "1.500,00", "1.500,00")])
        wizard = self.import_wizard(data_file).with_context(tz="America/Argentina/Buenos_Aires")
        message = wizard.action_test_import()["params"]["message"]
        self.assertIn("21", message)
        self.assertNotIn("20/08", message)

    def test_an_empty_cell_is_not_read_as_the_word_none(self):
        data_file = self.sheet([("21/08/2026", None, "1.500,00", "1.500,00")])
        _currency, _account, statements = self.parse(data_file)
        self.assertEqual(statements[0]["transactions"][0]["payment_ref"], "N/A")

    def test_a_test_import_of_an_empty_file_warns(self):
        wizard = self.import_wizard(self.sheet([]))
        self.assertEqual(wizard.action_test_import()["params"]["type"], "warning")

    def test_a_test_import_from_the_mapping_asks_for_a_file(self):
        from base64 import b64encode

        action = self.mapping.action_test_import_file()
        self.assertEqual(action["res_model"], "account.statement.import.sheet.mapping.test")
        self.assertEqual(action["context"]["default_mapping_id"], self.mapping.id)
        test = (
            self.env[action["res_model"]]
            .with_context(**action["context"])
            .create(
                {
                    "journal_id": self.journal.id,
                    "statement_file": b64encode(self.sheet([("21/08/2026", "Pago", "1.500,00", "1.500,00")])),
                    "statement_filename": "statement.xlsx",
                }
            )
        )
        self.assertEqual(test.mapping_id, self.mapping)
        statements = self.env["account.bank.statement"].search_count([])
        result = test.action_test()
        self.assertEqual(result["params"]["type"], "success")
        # and it leaves the user on the test wizard, file and journal included
        self.assertEqual(result["params"]["next"]["res_model"], test._name)
        self.assertEqual(result["params"]["next"]["res_id"], test.id)
        self.assertEqual(self.env["account.bank.statement"].search_count([]), statements)

    def test_a_failing_test_import_offers_the_preview(self):
        mapping = self.new_mapping(name="Roto", timestamp_column="NoExiste")
        wizard = self.import_wizard(self.sheet([("21/08/2026", "Pago", "1.500,00", "1.500,00")]), mapping)
        with self.assertRaises(RedirectWarning) as catcher:
            wizard.action_test_import()
        self.assertIn("expects a column named 'NoExiste'", catcher.exception.args[0])
