.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============================
Bank Statement Sheet Import UX
===============================

Most of the support around the statement sheet import comes from mappings that
do not match the file the bank exports: a renamed header, a header row on the
wrong line, the thousands separator the other way around. The error the user
gets back (``'Debits' is not in list``) says nothing about which part of the
mapping is wrong.

 * Adds a **"Preview Mapping"** button on the statement sheet mapping. It shows a
   sample sheet, with column letters and row numbers, built from the mapping as
   it is configured right now: where the header row must be, which columns must
   exist, and how dates and amounts must be written. Three sample transactions
   are filled in so the layout is unambiguous.
 * The sample can be downloaded as an **xlsx** file. Every cell is written as
   text, the way the parser reads them, so the sample file can be imported with
   that very mapping to check it end to end before fighting with the real
   statement.
 * The preview reads the mapping back to the user in plain words (date format,
   separators, ignored rows and columns) and **warns about the configurations
   that are going to fail**: a header row number of 0 (the header row is then
   read as a transaction too and the spreadsheet import fails), or column names
   on a mapping declared as having no header line.
 * Rewrites the error of a **failed import**. Instead of the bare
   ``'Date' is not in list``, it names the mapping and the column that is
   missing (or the date format that does not match, or the encoding that could
   not be detected, or the unsupported file format), and offers a button that
   opens **the preview of that mapping** right there. The raw parser error is
   kept, labelled as the technical detail, at the end.
 * Adds a **"Test Import"** button, on the mapping and next to "Import and View"
   in the import wizard. It reads a real file the way an import would and reports
   what would come in — how many transactions and between which dates — and
   leaves the wizard open with the file still loaded, so a mapping can be
   corrected and retested without picking the file again, **without saving
   anything**: no statement, no transaction, and not even the
   ``bank_statements_source`` of the journal that a real import writes. A file
   that cannot be read fails with the same explained error as an import.
 * **Explains the date format** instead of leaving the user to guess it. The
   preview reads it back in words (``%d/%m/%Y`` is ``day/month/year``) and lists
   the codes, highlighting the ones this mapping uses; the field help carries a
   short version of the same legend.
 * **Warns about the two other configurations that break an import**: rows
   skipped at the top of a file that has no header line, which are transactions
   and not headers; and amount columns the amount type does not read, which the
   mapping nevertheless demands the file to contain and which corrupt the amount
   when they arrive empty.
 * Reads **month names in Spanish**. ``strptime`` only knows the English ones, so
   a file with ``21-Ago-2026`` and a format of ``%d-%b-%Y`` used to fail; both
   spellings now work, in the short and the long form.
 * Keeps the **numeric cells of an xlsx native**. An amount stored as a number
   used to be stringified before parsing, which prints python notation: a dot as
   the decimal separator. A mapping configured with a comma then dropped that dot
   and shifted the amount by a factor of ten or a hundred, a different factor per
   value, so there was no multiple to apply afterwards.
 * **Refuses a decimal mark the mapping does not account for.** A thousands
   separator always groups three digits, so a "." or a "," followed by fewer than
   three digits at the end of a value can only be a decimal mark; when it is
   neither of the configured separators the import now stops with an explanation
   instead of importing a wrong amount.
 * Matches the configured column names **ignoring case and padding**, so a bank
   that exports ``DATE`` one month and ``Date`` the next one does not break the
   import.
 * Renames the ``Header lines skip count`` field to **Header row number** and
   explains what the number means, which is where most of the wrong mappings
   come from.
 * Clears the amount columns when the **Amount type** changes, so a mapping
   cannot keep columns that no longer apply to it.
 * Stops rendering the statement PDF while a file is being imported. With
   Enterprise installed, creating a bank statement renders its PDF
   synchronously, and on a statement of a few hundred lines that render is what
   makes the import time out. The attachment is also of no use to somebody who
   is importing the file they already have.

Technical notes
===============

 * The preview is built by ``account.statement.import.sheet.mapping._preview_layout()``,
   which follows what the parser actually does: the header sits on
   ``max(header_lines_skip_count, 1)`` and the transactions start right after
   ``header_lines_skip_count``. Ignored rows carry a label so that they exist in
   the exported file and the row numbers do not shift.
 * With ``no_header`` the mapping holds column indexes, so each field lands on
   the position it declares. With a header the file order is irrelevant to the
   parser, so the preview lays the columns out in the order of the form and says
   so.
 * ``_get_column_indexes`` rewrites the header cells that match a configured
   name to the configured spelling and delegates to the standard lookup, instead
   of duplicating it. An unknown column still raises.
 * ``_parse_decimal`` short-circuits ``Decimal``, ``int`` and ``float``: a number
   carries no separator to interpret, and letting an ``int`` reach the regex of
   the standard method raises ``TypeError``. The check of the decimal mark runs
   on what is left, the strings.
 * ``_get_xlsx_row_values`` is rewritten rather than extended, because the
   standard method offers no hook per cell. It is the only method of this module
   that duplicates code from the base one, so the per-cell rule lives in
   ``_xlsx_cell_value``: the next one extends that hook instead of forking the
   fork again. The fix belongs upstream, and the docstrings name the pull
   requests being mirrored.
 * The month names are translated in ``_get_values_from_column``, the smallest
   seam the parser offers, only for the timestamp column and only for a value
   that actually holds letters. Which language the bank writes its months in is
   really a property of the mapping; until there is a field for it, Spanish is
   accepted next to English because that is the region this is written for.
 * The redirect of a failed import goes through an ``ir.actions.server``: the
   failed import rolled its transaction back, so a preview record created on that
   path would no longer exist by the time the user clicks the button. The server
   action creates it when clicked, and falls back to the list of mappings if it
   is run without the mapping in the context.
 * The preview follows the journal being imported into, not the company, for
   the currency it writes in the sample and for the decimals it shifts by when
   no separator is configured: the parser reads both off the journal, and a line
   whose currency does not match it is dropped.
 * An empty xlsx cell is read as empty text. ``str()`` on what openpyxl returns
   for a blank cell hands the parser the word ``None``, which is truthy: it lands
   in the statement as a description, and on a debit/credit pair it turns the
   amount into zero.
 * The test import mirrors ``import_single_statement`` up to, and not including,
   the two steps that touch the database: the creation of the statements and the
   write of ``bank_statements_source`` on the journal. The import wizard it uses
   is a ``new()`` record when the test comes from the mapping, so not even that
   is written. It therefore does not see the transactions the real import would
   skip as already imported; running the real path inside a rolled-back
   savepoint, the way ``base_import`` does its dry run, would.
 * ``_parse_file`` re-raises a ``SheetMappingError``, a ``UserError`` subclass,
   and only the entry points a human clicks (``import_file_button`` and the test
   import) turn it into the ``RedirectWarning`` that offers the preview. Those
   entry points also explain a plain ``UserError`` whose message reads like a
   mapping failure, because the failure does not always come through
   ``_parse_file``: with ``account_statement_import_sheet_file_bg`` installed --
   and its row limit is set by default, so this is the usual path -- the split
   of the file runs first, calls the parser itself and re-raises whatever went
   wrong as a message of its own.
   ``RedirectWarning`` is not a ``UserError``, so raising it deeper would stop a
   cron importer, or another extension of ``_parse_file``, from catching the
   failure at all.
 * The redirect goes through an ``ir.actions.server`` rather than a prepared
   preview record, because the failed import rolled its transaction back and any
   record created on that path would be gone by the time the user clicks.
 * The hint is chosen by reading the raw message, which is the only thing the
   base module leaves to work with: it flattens the parser exception into
   ``UserError(_("Bad file/mapping: ") + str(exc))``. A message that is already
   one of ours gets no hint and is shown as it is.
 * ``skip_pdf_attachment_generation`` is added to the per-statement
   ``creation_context``, which is the seam the base module exposes: it pops that
   key off the values and passes it to the ``create`` of the statement.
   ``account_accountant`` reads it there to decide whether to call
   ``action_generate_attachment()``; Odoo itself skips the render the same way
   when importing statements (``l10n_be_codabox``, ``l10n_be_codaclean``), and
   without Enterprise the flag is a no-op.

Installation
============

Only install the module. It is auto installed as soon as
``account_statement_import_sheet_file`` is installed, and it pulls
``account_statement_import_sheet_file_xls`` and
``account_statement_import_sheet_file_xlsx`` with it, so a base that can import
csv statements can also import xls and xlsx ones.

Configuration
=============

This module does not need any configuration.

Usage
=====

Go to "Accounting > Configuration > Statement Sheet Mappings", open a mapping and
click "Preview Mapping".

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/miscellaneous/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
