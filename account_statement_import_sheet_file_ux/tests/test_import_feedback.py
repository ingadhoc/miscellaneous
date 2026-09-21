from unittest.mock import patch

from odoo.addons.account_statement_import_sheet_file.wizard.account_statement_import import (
    AccountStatementImport as SheetImport,
)
from odoo.addons.account_statement_import_sheet_file_ux.wizard.account_statement_import import (
    SheetMappingError,
)
from odoo.exceptions import RedirectWarning, UserError

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

    def test_the_button_override_does_not_narrow_the_signature(self):
        """`..._bg` re-enters `import_file_button` from its job with a kwarg.

        This module's override sits in front of it, so declaring it as `(self)`
        makes every background import die with a TypeError and save nothing.
        """
        import inspect

        from ..wizard import account_statement_import as wizard_module

        kinds = [
            parameter.kind
            for parameter in inspect.signature(
                wizard_module.AccountStatementImport.import_file_button
            ).parameters.values()
        ]
        self.assertIn(inspect.Parameter.VAR_KEYWORD, kinds)
        self.assertIn(inspect.Parameter.VAR_POSITIONAL, kinds)

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

    # What the test import promises

    def test_a_test_import_reports_what_the_import_creates(self):
        """The report and the import have to find the same thing in a file.

        ``_test_import_file`` mirrors ``import_single_statement`` by hand, for
        want of a hook between its analysis and its writes. This is what fails
        the day the two drift apart, instead of a user being told a file is
        ready and the import then refusing it.
        """
        data_file = self.sheet(
            [
                ("21/08/2026", "Pago", "1.500,00", "1.500,00"),
                ("22/08/2026", "Cobro", "-250,50", "1.249,50"),
                ("23/08/2026", "Comision", "-35,75", "1.213,75"),
            ]
        )
        reported = self.import_wizard(data_file)._test_import_file(data_file)
        # the context the background job runs its own import with: without it,
        # `_bg` enqueues the file instead of importing it and nothing is created
        self.import_wizard(data_file).with_context(bg_job=True).import_file_button()
        created = self.env["account.bank.statement.line"].search([("journal_id", "=", self.journal.id)])
        self.assertEqual(len(reported), len(created), "the report and the import disagree on how many lines")
        self.assertEqual(
            sorted(round(float(transaction["amount"]), 2) for transaction in reported),
            sorted(round(amount, 2) for amount in created.mapped("amount")),
        )

    # Which mistake the message names

    def test_a_header_read_as_a_transaction_is_named_as_such(self):
        """The header row number, not the date format.

        With the header row number at 0 the mapping reads its own headers as a
        transaction, and the first thing that breaks is the date -- so the
        parser complains about the format of a date that was never one, and
        sends the user to fix a field that is right.
        """
        mapping = self.new_mapping(header_lines_skip_count=0)
        wizard = self.import_wizard(self.sheet([("21/08/2026", "Pago", "1.500,00", "1.500,00")]), mapping)
        with self.assertRaises(RedirectWarning) as catcher:
            wizard.action_test_import()
        message = catcher.exception.args[0]
        self.assertIn("The header row number is 0", message)
        self.assertNotIn("Timestamp format", message)

    def test_a_date_the_file_really_writes_differently_still_blames_the_format(self):
        """The control case: the header is skipped, so the date is the problem."""
        wizard = self.import_wizard(self.sheet([("2026-08-21", "Pago", "1.500,00", "1.500,00")]))
        with self.assertRaises(RedirectWarning) as catcher:
            wizard.action_test_import()
        message = catcher.exception.args[0]
        self.assertIn("Timestamp format", message)
        self.assertNotIn("The header row number is 0", message)

    def test_the_preview_of_a_mapping_opens_for_an_accountant(self):
        """The button of the error message is useless to whoever imports.

        A server action with no groups demands write access on its model, and
        only an accounting manager has it on the mappings -- so an accountant
        was told they are not allowed to look at a preview.
        """
        action = self.env.ref("account_statement_import_sheet_file_ux.action_preview_mapping_from_error")
        self.assertIn(self.env.ref("account.group_account_user"), action.group_ids)

    # Whose failure is it

    def test_an_error_from_another_module_is_not_blamed_on_the_mapping(self):
        """Only what the sheet parser wrapped gets explained as a mapping problem.

        Another override of ``_parse_file`` raising an error of its own has no
        cause underneath, and its message has to reach the user untouched --
        being sent to fix the mapping would be a wrong turn.
        """
        wizard = self.import_wizard(self.sheet([("21/08/2026", "Pago", "1.500,00", "1.500,00")]))
        message = "This file belongs to another journal"

        def raise_its_own(_self, _data_file):
            raise UserError(message)

        with patch.object(SheetImport, "_parse_file", raise_its_own):
            with self.assertRaises(UserError) as catcher:
                wizard._parse_file(b"whatever")
        self.assertEqual(str(catcher.exception), message)

    def test_a_translated_message_still_offers_the_preview(self):
        """The offer cannot hang on English words only.

        ``_bg`` re-raises a failure as a plain UserError carrying the text of
        the original, and on a database in Spanish that text arrives already
        translated -- so no English signal matches it. The type of the
        exception it kept as its context is what still says whose failure it
        was.
        """
        wizard = self.import_wizard(self.sheet([("21/08/2026", "Pago", "1.500,00", "1.500,00")]))
        translated = "No se puede leer el importe 1500.50: usa . como marca decimal"

        def like_the_background_job():
            try:
                raise SheetMappingError(translated)
            except SheetMappingError as error:
                raise UserError(f"Error importing bank statement: {error}") from None

        with self.assertRaises(RedirectWarning) as catcher:
            with wizard._offer_the_preview():
                like_the_background_job()
        self.assertIn(translated, catcher.exception.args[0])

    def test_this_module_loads_above_bg(self):
        """The wrapper of the button only works from above ``_bg``.

        Odoo sorts the load by the depth of the dependency graph, and this
        module sits one level deeper. If that ever inverts, the background job
        is enqueued before the wrapper sees anything and a failed import stops
        offering the preview.
        """
        loaded = [klass.__module__ for klass in type(self.env["account.statement.import"]).mro()]
        background = "odoo.addons.account_statement_import_sheet_file_bg.models.account_statement_import"
        this = "odoo.addons.account_statement_import_sheet_file_ux.wizard.account_statement_import"
        if background not in loaded:
            self.skipTest("account_statement_import_sheet_file_bg is not installed")
        self.assertLess(loaded.index(this), loaded.index(background), "this module no longer wraps the background one")
