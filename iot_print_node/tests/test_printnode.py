import base64
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

REQUESTS = "odoo.addons.iot_print_node.models.printnode_account.requests"


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


@tagged("post_install", "-at_install")
class TestPrintnode(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env["printnode.account"].create({"name": "Office", "print_node_api_key": "secret"})
        cls.report = cls.env.ref("base.ir_module_reference_print")
        cls.doc = cls.env.ref("base.module_base")

    def _sync(self, pn_printers):
        with patch(REQUESTS) as requests_mock:
            requests_mock.get.return_value = _response(pn_printers)
            self.account.action_print_update_devices()
        return requests_mock

    def test_update_devices_creates_updates_and_deletes_printers(self):
        requests_mock = self._sync(
            [
                {"id": 1, "description": "Zebra", "state": "online"},
                {"id": 2, "description": "HP", "state": "offline"},
            ]
        )
        url = requests_mock.get.call_args.args[0]
        self.assertEqual(url, "https://api.printnode.com/printers")
        auth = requests_mock.get.call_args.kwargs["headers"]["authorization"]
        self.assertEqual(auth, "Basic " + base64.b64encode(b"secret").decode())

        printers = self.account.printer_ids
        self.assertEqual(sorted(printers.mapped("printnode_identifier")), ["1", "2"])
        self.assertEqual(set(printers.mapped("type")), {"printnode"})
        zebra = printers.filtered(lambda p: p.printnode_identifier == "1")
        self.assertEqual(zebra.name, "Zebra")
        self.assertEqual(zebra.printnode_status, "connected")
        hp = printers.filtered(lambda p: p.printnode_identifier == "2")
        self.assertEqual(hp.printnode_status, "disconnected")

        self._sync([{"id": 1, "description": "Zebra ZD421", "state": "offline"}])
        self.assertEqual(self.account.printer_ids, zebra)
        self.assertEqual(zebra.name, "Zebra ZD421")
        self.assertEqual(zebra.printnode_status, "disconnected")
        self.assertFalse(hp.exists())

    def test_connection_error_raises_user_error(self):
        import requests

        with patch(REQUESTS) as requests_mock:
            requests_mock.RequestException = requests.RequestException
            requests_mock.get.side_effect = requests.ConnectionError()
            with self.assertRaises(UserError):
                self.account.action_print_update_devices()

    def test_get_print_jobs_and_print(self):
        self._sync([{"id": 7, "description": "Zebra", "state": "online"}])
        printer = self.account.printer_ids
        self.report.printer_ids = printer

        with patch.object(type(self.report), "_render", return_value=(b"%PDF-1.4 test", "pdf")):
            jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        printnode_jobs = [job for job in jobs if job["type"] == "printnode"]
        self.assertEqual(len(printnode_jobs), 1)
        job = printnode_jobs[0]
        self.assertEqual(job["printnode_type"], "pdf")
        self.assertEqual(base64.b64decode(job["report"]), b"%PDF-1.4 test")

        with patch(REQUESTS) as requests_mock:
            requests_mock.post.return_value = _response(123)
            printer.printnode_print(job)
        url = requests_mock.post.call_args.args[0]
        self.assertEqual(url, "https://api.printnode.com/printjobs")
        payload = requests_mock.post.call_args.kwargs["json"]
        self.assertEqual(payload["printerId"], "7")
        self.assertEqual(payload["contentType"], "pdf_base64")
        self.assertEqual(payload["content"], job["report"])

    def test_no_job_without_printnode_printer(self):
        jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        self.assertFalse([job for job in jobs if job["type"] == "printnode"])

    def test_unsupported_report_type_raises(self):
        self._sync([{"id": 7, "description": "Zebra", "state": "online"}])
        printer = self.account.printer_ids
        with self.assertRaises(UserError):
            printer.printnode_print({"type": "printnode", "report_type": "qweb-html", "printnode_type": None})

    def test_wizard_creates_account_and_syncs(self):
        wizard = self.env["add.printnode.account"].create({"name": "Warehouse", "print_node_api_key": "key2"})
        with patch(REQUESTS) as requests_mock:
            requests_mock.get.return_value = _response([{"id": 9, "description": "Brother", "state": "online"}])
            action = wizard.action_add_printnode_account()
        account = self.env["printnode.account"].browse(action["res_id"])
        self.assertEqual(account.name, "Warehouse")
        self.assertEqual(account.printer_ids.printnode_identifier, "9")
