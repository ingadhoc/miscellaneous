##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import csv
import io
import json
import re
import zipfile
from unittest.mock import patch

from odoo.tests.common import TransactionCase, new_test_user


class TestExportBg(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partners = cls.env["res.partner"].create([{"name": f"Export BG Partner {i}"} for i in range(5)])
        cls.env["ir.config_parameter"].sudo().set_str("export_bg.record_threshold", "2")
        cls.export_user = new_test_user(
            cls.env,
            login="export_bg_user",
            groups="base.group_user,base.group_allow_export",
        )

    def _export(self, export_format, user=None):
        """Enqueue the export of the test partners and run its jobs in order, as the cron would."""
        data = {
            "model": "res.partner",
            "fields": [{"name": "name", "label": "Name"}],
            "ids": self.partners.ids,
            "domain": [],
            "context": {},
            "import_compat": False,
        }
        env = self.env(user=user) if user else self.env
        _action, jobs = env["ir.model"].web_export(json.dumps(data), export_format)
        self.assertEqual(len(jobs), 3, "5 records with a threshold of 2 must give 3 chunks")
        results = []
        with (
            patch.object(self.env.cr, "commit"),
            patch.object(self.env.cr, "rollback"),
            patch.object(type(self.env["bg.job"]), "_notify_user", lambda job, result: results.append(result)),
        ):
            for job in jobs.sudo():
                self.assertEqual(job.state, "enqueued")
                job.state = "running"
                job.run()
                self.assertEqual(job.state, "done", job.error_message)
        self.assertEqual(len(results), 1, "only the last job returns the download message")
        return jobs, results[0]

    def _get_final_attachment(self, message):
        att_id = int(re.search(r"/web/content/(\d+)\?download=true", message).group(1))
        return self.env["ir.attachment"].sudo().browse(att_id)

    def _assert_no_chunks_left(self, jobs):
        export_id = jobs[0].kwargs_json["export_id"]
        chunks = self.env["ir.attachment"].sudo().search([("description", "=", export_id)])
        self.assertFalse(chunks, "the intermediate chunks must be deleted after combining them")

    def test_export_threshold(self):
        self.assertEqual(self.env["ir.model"].get_export_threshold(), 2)
        self.env["ir.config_parameter"].sudo().search([("key", "=", "export_bg.record_threshold")]).unlink()
        self.assertEqual(self.env["ir.model"].get_export_threshold(), 500)

    def test_export_csv_in_chunks(self):
        jobs, message = self._export("csv")
        self.assertIn('data-icon="download"', message)
        attachment = self._get_final_attachment(message)
        self.assertEqual(attachment.name, "export.csv")
        rows = list(csv.reader(io.StringIO(attachment.raw.content.decode())))
        self.assertEqual(rows, [["Name"]] + [[name] for name in self.partners.mapped("name")])
        self._assert_no_chunks_left(jobs)

    def test_export_xlsx_in_chunks(self):
        jobs, message = self._export("xlsx")
        attachment = self._get_final_attachment(message)
        self.assertTrue(attachment.name.endswith(".xlsx"))
        with zipfile.ZipFile(io.BytesIO(attachment.raw.content)) as xlsx:
            sheet = xlsx.read("xl/worksheets/sheet1.xml").decode()
            strings = xlsx.read("xl/sharedStrings.xml").decode()
        self.assertEqual(len(re.findall(r"<row ", sheet)), 6, "header plus one row per record")
        for value in ["Name", *self.partners.mapped("name")]:
            self.assertIn(f">{value}<", strings)
        self._assert_no_chunks_left(jobs)

    def test_export_by_internal_user(self):
        """A user that is not an administrator exports in background with their own jobs and chunks."""
        jobs, message = self._export("csv", user=self.export_user)
        self.assertEqual(jobs.create_uid, self.export_user)
        attachment = self._get_final_attachment(message)
        self.assertEqual(attachment.create_uid, self.export_user)
        rows = list(csv.reader(io.StringIO(attachment.raw.content.decode())))
        self.assertEqual(rows, [["Name"]] + [[name] for name in self.partners.mapped("name")])
        self._assert_no_chunks_left(jobs)
