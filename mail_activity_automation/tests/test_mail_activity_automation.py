from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestMailActivityAutomation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.partner = cls.env["res.partner"].create({"name": "Automation Partner"})
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.template = cls.env["mail.template"].create(
            {
                "name": "Automatic reminder",
                "model_id": cls.partner_model.id,
                "subject": "Automatic reminder",
                "body_html": "<p>AUTOMATIC-REMINDER-BODY</p>",
            }
        )
        cls.type_auto_template = cls._create_type("Auto with template", True, cls.template)
        cls.type_auto_no_template = cls._create_type("Auto without template", True)
        cls.type_manual = cls._create_type("Manual", False, cls.template)

    @classmethod
    def _create_type(cls, name, run_automatically, template=None):
        return cls.env["mail.activity.type"].create(
            {
                "name": name,
                "res_model": "res.partner",
                "run_automatically": run_automatically,
                "mail_template_ids": [(6, 0, template.ids if template else [])],
            }
        )

    def _create_activity(self, activity_type, days):
        return self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_model_id": self.partner_model.id,
                "res_id": self.partner.id,
                "user_id": self.env.user.id,
                "date_deadline": self.today + relativedelta(days=days),
            }
        )

    def _template_messages(self):
        return self.partner.message_ids.filtered(lambda m: "AUTOMATIC-REMINDER-BODY" in (m.body or ""))

    def _is_done(self, activity):
        activity = activity.with_context(active_test=False)
        return not activity.active and bool(activity.date_done)

    def test_cron_runs_due_automatic_activities(self):
        due_with_template = self._create_activity(self.type_auto_template, -1)
        due_without_template = self._create_activity(self.type_auto_no_template, -1)
        not_due = self._create_activity(self.type_auto_template, 1)
        due_manual_type = self._create_activity(self.type_manual, -1)
        activity_ids_before = self.env["mail.activity"].with_context(active_test=False).search([]).ids

        self.env["mail.activity"]._cron_run_activities()

        self.assertTrue(self._is_done(due_with_template))
        self.assertTrue(self._is_done(due_without_template))
        self.assertFalse(self._is_done(not_due))
        self.assertFalse(self._is_done(due_manual_type))

        template_messages = self._template_messages()
        self.assertEqual(len(template_messages), 1, "Only the due activity with a template sends it, once")
        self.assertEqual(template_messages.subtype_id, self.env.ref("mail.mt_comment"))

        done_messages = self.partner.message_ids.filtered(
            lambda m: m.mail_activity_type_id in (self.type_auto_template | self.type_auto_no_template)
        )
        self.assertEqual(len(done_messages), 2, "Each executed activity logs its done message")
        new_activities = (
            self.env["mail.activity"].with_context(active_test=False).search([("id", "not in", activity_ids_before)])
        )
        self.assertFalse(new_activities, "No follow-up activity is created")

    def test_manual_done_does_not_send_template(self):
        activity = self._create_activity(self.type_auto_template, -1)
        not_due = self._create_activity(self.type_auto_template, 10)

        activity.action_done()
        # the old bot context key must not trigger the automatic run anymore
        not_due.with_context(from_bot=True).action_done()

        self.assertTrue(self._is_done(activity))
        self.assertTrue(self._is_done(not_due))
        self.assertFalse(self._template_messages())

    @mute_logger("odoo.addons.mail_activity_automation.models.mail_activity")
    def test_cron_isolates_failing_activities(self):
        generic_type = self.env["mail.activity.type"].create({"name": "Auto generic", "run_automatically": True})
        without_document = self.env["mail.activity"].create(
            {
                "activity_type_id": generic_type.id,
                "user_id": self.env.user.id,
                "date_deadline": self.today - relativedelta(days=1),
            }
        )
        failing = self._create_activity(self.type_auto_no_template, -1)
        good = self._create_activity(self.type_auto_template, -1)
        activity_class = type(self.env["mail.activity"])
        original_run = activity_class._run_automatically

        def run_or_fail(activity):
            if activity == failing:
                raise ValueError("Simulated failure")
            return original_run(activity)

        with patch.object(activity_class, "_run_automatically", autospec=True, side_effect=run_or_fail):
            self.env["mail.activity"]._cron_run_activities()

        self.assertFalse(self._is_done(without_document), "Activities without document are skipped")
        self.assertFalse(self._is_done(failing))
        self.assertTrue(self._is_done(good), "A failing activity does not block the others")
        self.assertEqual(len(self._template_messages()), 1)
