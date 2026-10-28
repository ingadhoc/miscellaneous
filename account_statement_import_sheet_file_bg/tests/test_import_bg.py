import base64
import csv
from io import BytesIO, StringIO

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from openpyxl import Workbook

LIMIT_PARAM = "account_statement_import_sheet_file_bg.rows_per_file_limit"


@tagged("post_install", "-at_install")
class TestImportBg(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        suspense = cls.env["account.account"].create(
            {"code": "987654", "name": "Suspense", "account_type": "asset_current"}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Bank BG", "type": "bank", "code": "BKBG", "suspense_account_id": suspense.id}
        )
        # the header is the third line: a title and an empty line come before it
        cls.mapping = cls.env["account.statement.import.sheet.mapping"].create(
            {
                "name": "BG",
                "header_lines_skip_count": 3,
                "delimiter": "comma",
                "float_thousands_sep": "none",
                "float_decimal_sep": "dot",
                "timestamp_format": "%Y-%m-%d",
                "timestamp_column": "Date",
                "amount_type": "simple_value",
                "amount_column": "Amount",
                "description_column": "Label",
            }
        )
        cls.labels = [f"Line {i}" for i in range(1, 6)]
        cls.rows = [["Bank report"], [], ["Date", "Label", "Amount"]]
        cls.rows += [[str(cls.today - relativedelta(days=i)), label, "10.00"] for i, label in enumerate(cls.labels)]
        # a subtotal row without date, which no part should carry
        cls.rows.append(["", "Subtotal", "50.00"])

    def _file(self, kind):
        if kind == "csv":
            buffer = StringIO()
            csv.writer(buffer).writerows(self.rows)
            return base64.b64encode(buffer.getvalue().encode())
        workbook = Workbook()
        for row in self.rows:
            # an empty cell at the end of the header, read as "" and not "None"
            workbook.active.append(row + [None] if row and row[0] == "Date" else row)
        buffer = BytesIO()
        workbook.save(buffer)
        return base64.b64encode(buffer.getvalue())

    def _wizard(self, kind="csv", mapping=True):
        return (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal.id)
            .create(
                {
                    "statement_filename": f"statement.{kind}",
                    "statement_file": self._file(kind),
                    "sheet_mapping_id": self.mapping.id if mapping else False,
                }
            )
        )

    def _jobs(self):
        return self.env["bg.job"].search([("model", "=", "account.statement.import")], order="id")

    def _run(self, job):
        """Run the job method the way bg.job.run does, without its commits."""
        context = dict(job.context_json or {}, bg_job=True, bg_job_id=job.id)
        kwargs = dict(job.kwargs_json)
        kwargs.pop("_record_ids")
        return getattr(self.env[job.model].with_context(**context), job.method)(**kwargs)

    def _statements(self):
        return self.env["account.bank.statement"].search([("journal_id", "=", self.journal.id)], order="id")

    def test_import_in_parts_chain(self):
        """With the row limit set, the file is split in parts imported by background jobs.

        Covers: each part keeps the header rows (also when empty rows come before
        the header in a csv), rows without date go to no part, one job per part,
        each statement named "Part i/n", and no line lost or repeated.
        """
        if not hasattr(self.env["account.statement.import.sheet.parser"], "_parse_lines_xlsx"):
            # the parts are written as xlsx, and the module does not depend on the reader
            self.skipTest("account_statement_import_sheet_file_xlsx is not installed")
        self.env["ir.config_parameter"].set_param(LIMIT_PARAM, "2")
        for kind in ("csv", "xlsx"):
            with self.subTest(kind=kind):
                self._jobs().unlink()
                self._statements().unlink()
                with self.subTest("the button enqueues three jobs, one per part"):
                    action = self._wizard(kind).import_file_button()
                    self.assertEqual(action["tag"], "display_notification")
                    jobs = self._jobs()
                    self.assertEqual(
                        jobs.mapped("name"),
                        [f"account.statement.import.import_file_button - Part {i}/3" for i in (1, 2, 3)],
                    )
                    self.assertFalse(self._statements())
                with self.subTest("each job creates its statement with 'Part i/3' in the name"):
                    for job in jobs:
                        message = self._run(job)
                        self.assertIn("The following bank statement has been created", message)
                    self.assertEqual(
                        [name.rsplit(" - ", 1)[1] for name in self._statements().mapped("name")],
                        ["Part 1/3", "Part 2/3", "Part 3/3"],
                    )
                with self.subTest("the three statements add up to the five dated rows, none repeated"):
                    lines = self._statements().line_ids
                    self.assertEqual(sorted(lines.mapped("payment_ref")), self.labels)
                    self.assertEqual([len(st.line_ids) for st in self._statements()], [2, 2, 1])

    def test_import_runs_now_without_limit(self):
        """Without the row limit the import runs right away, with no background job.

        Also with nothing to split (no mapping, or no dated rows) even with the limit
        set: a file that cannot be imported raises in the wizard, not in a background job.
        """
        self.env["ir.config_parameter"].set_param(LIMIT_PARAM, False)
        # the OCA csv parser drops empty lines and fails on a row without date,
        # which only the split takes out: this file has neither
        self.rows = self.rows[2:-1]
        self.mapping.header_lines_skip_count = 1
        self._wizard().import_file_button()
        self.assertFalse(self._jobs())
        self.assertEqual(sorted(self._statements().line_ids.mapped("payment_ref")), self.labels)
        for value in (False, "2"):
            with self.subTest(
                "without mapping, the import runs right away and its error reaches the wizard", limit=value
            ):
                self.env["ir.config_parameter"].set_param(LIMIT_PARAM, value)
                with self.assertRaisesRegex(UserError, "format is not supported"):
                    self._wizard(mapping=False).import_file_button()
                self.assertFalse(self._jobs())
        with self.subTest("a sheet without dated rows has nothing to split and imports right away"):
            self.env["ir.config_parameter"].set_param(LIMIT_PARAM, "2")
            self.rows = self.rows[:1]
            with self.assertRaisesRegex(UserError, "already imported"):
                self._wizard().import_file_button()
            self.assertFalse(self._jobs())
