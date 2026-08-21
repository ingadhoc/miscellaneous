import base64
import re
from contextlib import contextmanager

from odoo import models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools.misc import format_date

# What a failed sheet mapping looks like in a message. Needed because the
# failure does not always travel as an exception of ours: with
# `account_statement_import_sheet_file_bg` installed -- and its row limit is set
# by default -- the split of the file runs before `_parse_file`, calls the
# parser itself, and re-raises whatever went wrong as a plain UserError.
MAPPING_FAILURE_SIGNALS = (
    "is not in list",
    "does not match format",
    "No valid encoding",
    "Unsupported sheet type",
    "Cannot read the amount",
)


class SheetMappingError(UserError):
    """A failed import that the preview of the sheet mapping can explain.

    A subclass so that the interactive entry points can offer that preview
    without the deeper code having to know whether a human is watching, and
    still a UserError so that everything catching one keeps catching this.
    """


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    # A failed import

    def _parse_file(self, data_file):
        """Explain a failed sheet import instead of leaking the parser error.

        The standard message ("'Date' is not in list") says nothing about what
        to do next, and the answer is almost always the same: the mapping does
        not describe the file the bank exported.
        """
        try:
            return super()._parse_file(data_file)
        except UserError as error:
            mapping = self.sheet_mapping_id
            if not mapping:
                raise
            raise SheetMappingError(self._sheet_mapping_error_message(mapping, str(error))) from error

    @contextmanager
    def _offer_the_preview(self):
        """Turn a mapping failure into an offer to open its preview.

        Only around what a human clicks. The offer is a ``RedirectWarning``,
        which is not a ``UserError``, so raising it deeper would quietly stop a
        cron importer, or another extension of ``_parse_file``, from catching
        the failure at all.
        """
        try:
            yield
        except UserError as error:
            mapping = self.sheet_mapping_id
            if not mapping:
                raise
            message = str(error)
            if not isinstance(error, SheetMappingError):
                # the failure came from somewhere that does not know about the
                # mapping, so it is only worth explaining if it reads like one
                if not any(signal in message for signal in MAPPING_FAILURE_SIGNALS):
                    raise
                message = self._sheet_mapping_error_message(mapping, message)
            raise RedirectWarning(
                message,
                self.env.ref("account_statement_import_sheet_file_ux" ".action_preview_mapping_from_error").id,
                self.env._("See the preview"),
                {"preview_mapping_id": mapping.id},
            ) from error

    def import_file_button(self):
        with self._offer_the_preview():
            return super().import_file_button()

    def _sheet_mapping_error_message(self, mapping, message):
        """The explanation first, the raw parser error last.

        The raw error is kept because support needs it, but it is in English
        and comes straight from python, so it goes at the end and labelled.
        """
        self.ensure_one()
        hint = self._sheet_mapping_error_hint(mapping, message)
        if not hint:
            # the failure already explains itself, in the language of the user
            return message
        return "%s\n\n%s" % (hint, self.env._("Technical detail: %s", message))

    def _sheet_mapping_error_hint(self, mapping, message):
        """Turn a raw parser error into something the user can act on.

        Returns nothing when the message is already one of ours, which is the
        case for the amount whose decimal mark the mapping does not account
        for: it is the most actionable message of the lot and it would only
        lose by being demoted behind a generic one.
        """
        self.ensure_one()
        if "Cannot read the amount" in message:
            return None
        missing_column = re.search(r"'(.+?)' is not in list", message)
        if missing_column:
            return self.env._(
                "The mapping '%(mapping)s' expects a column named "
                "'%(column)s' and the file does not have it. Banks rename "
                "their columns from one export to the next: check the Columns "
                "section of the mapping and use the 'Preview Mapping' button "
                "to see the file the mapping is expecting.",
                mapping=mapping.name,
                column=missing_column.group(1),
            )
        if "does not match format" in message:
            return self.env._(
                "The mapping '%(mapping)s' reads the dates with the format "
                "'%(format)s' and the file writes them differently. Check the "
                "'Timestamp format' field of the mapping and use the 'Preview "
                "Mapping' button to see the file the mapping is expecting.",
                mapping=mapping.name,
                format=mapping.timestamp_format,
            )
        if "No valid encoding" in message:
            return self.env._(
                "The encoding of the file could not be detected, so none of it "
                "can be read. Ask for the file to be exported again from the "
                "bank, or saved as CSV UTF-8."
            )
        if "Unsupported sheet type" in message:
            return self.env._(
                "The format of this file is not one of the formats that can be "
                "read with a mapping: csv, txt, xls and xlsx."
            )
        return self.env._(
            "The file could not be read with the mapping '%s'. Use the "
            "'Preview Mapping' button on the mapping to see the file it is "
            "expecting and compare it with yours.",
            mapping.name,
        )

    # A test import

    def action_test_import(self, next_action=None):
        """Analyse the file the way an import would, without creating anything.

        ``next_action`` is where the user is left once the report is shown; by
        default back on this same wizard, with the file still loaded.
        """
        self.ensure_one()
        with self._offer_the_preview():
            transactions = self._test_import_file(base64.b64decode(self.statement_file))
        if next_action is None:
            next_action = self._reopen_wizard()
        return self._test_import_notification(transactions, next_action)

    def _reopen_wizard(self):
        """The action that puts this wizard back on screen, file included.

        A wizard button closes its dialog, so without this the user would have
        to open the import again and pick the same file a second time. Nothing
        to reopen when the record is virtual, which is the case for the test
        that comes from the mapping and brings its own wizard to return to.
        """
        self.ensure_one()
        if not isinstance(self.id, int):
            return None
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
            "context": dict(self.env.context),
        }

    def _test_import_file(self, data_file):
        """Return the transactions an import of this file would create.

        Mirrors ``import_single_statement`` of ``account_statement_import_file``
        up to, and not including, the two steps that touch the database: the
        creation of the statements and the write of ``bank_statements_source``
        on the journal. Kept in step with that method by hand, for want of a
        hook between its analysis and its writes.
        """
        self.ensure_one()
        # active_id is only read by the parsers of the other formats
        this = self.with_context(active_id=self.id) if isinstance(self.id, int) else self
        parsing_data = this._parse_file(data_file)
        if not isinstance(parsing_data, list):
            parsing_data = [parsing_data]
        transactions = []
        for single_statement_data in parsing_data:
            if not isinstance(single_statement_data, tuple):
                raise UserError(self.env._("The parsing of the statement file returned an invalid result."))
            currency_code, account_number, stmts_vals = single_statement_data
            if not self._check_parsed_data(stmts_vals):
                continue
            if not currency_code:
                raise UserError(self.env._("Missing currency code in the bank statement file."))
            currency = self._match_currency(currency_code)
            journal = self._match_journal(account_number, currency)
            if not journal.default_account_id:
                raise UserError(
                    self.env._(
                        "The Bank Accounting Account is not set on the journal '%s'.",
                        journal.display_name,
                    )
                )
            for st_vals in self._complete_stmts_vals(stmts_vals, journal, account_number):
                transactions += st_vals.get("transactions") or []
        return transactions

    def _test_import_notification(self, transactions, next_action=None):
        """Report the result of a test import without leaving the wizard."""
        self.ensure_one()
        if not transactions:
            return self._test_import_toast(
                next_action,
                "warning",
                self.env._("There is nothing to import in this file"),
                self.env._(
                    "The file was read with the mapping without any error, but "
                    "it has no transaction in it. Check the rows ignored at the "
                    "beginning and at the end of the file."
                ),
            )
        # the parser hands over naive datetimes at midnight, and format_date
        # would read them as UTC and shift the day in a negative offset
        dates = sorted(transaction["date"].date() for transaction in transactions)
        return self._test_import_toast(
            next_action,
            "success",
            self.env._("This file is ready to be processed"),
            self.env._(
                "Transactions found: %(count)s, from %(first)s to %(last)s. "
                "Nothing was saved: run the import itself to create the "
                "statement.",
                count=len(transactions),
                first=format_date(self.env, dates[0]),
                last=format_date(self.env, dates[-1]),
            ),
        )

    def _test_import_toast(self, next_action, kind, title, message):
        params = {
            "type": kind,
            "title": title,
            "message": message,
            "sticky": True,
        }
        if next_action:
            # what the notification hands back to the web client once shown
            params["next"] = next_action
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": params,
        }

    # The statement PDF

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        """Ask for the statements to be created without rendering their PDF.

        With Enterprise installed, creating a bank statement renders its PDF
        synchronously (`account_accountant` hooks `create` unless the context
        says otherwise). On a statement of a few hundred lines that render is
        what makes the import time out, and the attachment is of no use to
        somebody who is importing the file they already have. Odoo itself skips
        it the same way when importing (`l10n_be_codabox`, `l10n_be_codaclean`).

        `creation_context` is the seam the base module exposes for this: it
        pops it off the values and passes it to the create of the statement.
        """
        stmts_vals = super()._complete_stmts_vals(stmts_vals, journal, account_number)
        for st_vals in stmts_vals:
            st_vals.setdefault("creation_context", {})["skip_pdf_attachment_generation"] = True
        return stmts_vals
