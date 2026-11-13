import base64
from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

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

    def _printnode_printer(self):
        self._sync([{"id": 7, "description": "Zebra", "state": "online"}])
        printer = self.account.printer_ids
        self.report.printer_ids = printer
        return printer

    def _printnode_jobs(self, jobs):
        return [job for job in jobs if job["type"] == "printnode"]

    def test_get_print_jobs_does_not_render(self):
        self._printnode_printer()
        with patch.object(type(self.report), "_render") as render:
            jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        self.assertFalse(render.called)
        self.assertEqual(
            self._printnode_jobs(jobs),
            [{"type": "printnode", "report_id": self.report.id, "docids": self.doc.ids, "data": {}}],
        )

    def test_report_action_with_recordset(self):
        self._printnode_printer()
        action = self.report.report_action(self.doc)
        jobs = self._printnode_jobs(action["context"]["jobs"])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["docids"], self.doc.ids)

    def test_print_renders_as_user_and_sends_to_printnode(self):
        printer = self._printnode_printer()
        user = new_test_user(self.env, login="printnode_user", groups="base.group_user")
        job = self._printnode_jobs(self.report.get_print_jobs(self.report.report_name, self.doc.ids, {}))[0]
        render_envs = []

        def fake_render(report, report_ref, res_ids, data=None):
            render_envs.append((report.env.uid, report.env.su, res_ids))
            return b"%PDF-1.4 test", "pdf"

        with (
            patch.object(type(self.report), "_render", autospec=True, side_effect=fake_render),
            patch(REQUESTS) as requests_mock,
        ):
            requests_mock.post.return_value = _response(123)
            printer.with_user(user).printnode_print(job)

        self.assertEqual(render_envs, [(user.id, False, self.doc.ids)])
        url = requests_mock.post.call_args.args[0]
        self.assertEqual(url, "https://api.printnode.com/printjobs")
        payload = requests_mock.post.call_args.kwargs["json"]
        self.assertEqual(payload["printerId"], "7")
        self.assertEqual(payload["contentType"], "pdf_base64")
        self.assertEqual(base64.b64decode(payload["content"]), b"%PDF-1.4 test")

    def test_no_job_without_printnode_printer(self):
        jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        self.assertFalse(self._printnode_jobs(jobs))

    def test_print_report_not_linked_raises(self):
        printer = self._printnode_printer()
        self.report.printer_ids = False
        with self.assertRaises(UserError):
            printer.printnode_print({"type": "printnode", "report_id": self.report.id, "docids": self.doc.ids})

    def test_unsupported_report_type_raises(self):
        printer = self._printnode_printer()
        self.report.report_type = "qweb-html"
        with self.assertRaises(UserError):
            printer.printnode_print({"type": "printnode", "report_id": self.report.id, "docids": self.doc.ids})

    def test_internal_user_cannot_point_printer_to_printnode(self):
        printer = self._printnode_printer()
        user = new_test_user(self.env, login="printnode_user", groups="base.group_user")
        Printer = self.env["printer.printer"].with_user(user)
        with self.assertRaises(AccessError):
            Printer.create(
                {
                    "name": "Mine",
                    "type": "printnode",
                    "printnode_account_id": self.account.id,
                    "printnode_identifier": "999999",
                }
            )
        with self.assertRaises(AccessError):
            printer.with_user(user).write({"printnode_identifier": "999999"})
        printer.with_user(user).write({"name": "Zebra front"})
        self.assertEqual(printer.name, "Zebra front")

    def test_wizard_creates_account_and_syncs(self):
        wizard = self.env["add.printnode.account"].create({"name": "Warehouse", "print_node_api_key": "key2"})
        with patch(REQUESTS) as requests_mock:
            requests_mock.get.return_value = _response([{"id": 9, "description": "Brother", "state": "online"}])
            action = wizard.action_add_printnode_account()
        account = self.env["printnode.account"].browse(action["res_id"])
        self.assertEqual(account.name, "Warehouse")
        self.assertEqual(account.printer_ids.printnode_identifier, "9")
