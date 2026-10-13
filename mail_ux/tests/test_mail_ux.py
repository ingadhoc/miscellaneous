import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMailUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="mail_ux_user", groups="base.group_user,base.group_partner_manager")
        cls.partner = cls.env["res.partner"].create({"name": "Mail UX partner"})

    def test_user_can_set_own_send_message_delay(self):
        self.user.with_user(self.user).write({"send_message_delay": 30})
        self.assertEqual(self.user.send_message_delay, 30)
        self.assertEqual(self.user.with_user(self.user).read(["send_message_delay"])[0]["send_message_delay"], 30)

    def test_composer_schedules_message_when_delay_is_set(self):
        self.user.send_message_delay = 60
        messages_before = self.partner.message_ids
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.user)
            .with_context(default_model="res.partner", default_res_ids=self.partner.ids)
            .create({"body": "<p>Delayed</p>", "composition_mode": "comment"})
        )
        composer._action_send_mail()
        scheduled = self.env["mail.scheduled.message"].search(
            [("model", "=", "res.partner"), ("res_id", "=", self.partner.id)]
        )
        self.assertEqual(len(scheduled), 1)
        self.assertTrue(scheduled.scheduled_date)
        self.assertEqual(self.partner.message_ids, messages_before)

    def test_composer_sends_immediately_without_delay(self):
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.user)
            .with_context(default_model="res.partner", default_res_ids=self.partner.ids)
            .create({"body": "<p>Now</p>", "composition_mode": "comment"})
        )
        composer._action_send_mail()
        self.assertFalse(
            self.env["mail.scheduled.message"].search([("model", "=", "res.partner"), ("res_id", "=", self.partner.id)])
        )
        self.assertIn("Now", self.partner.message_ids[0].body)

    def test_mass_mail_with_delay_is_not_scheduled(self):
        self.user.send_message_delay = 60
        partners = self.partner | self.env["res.partner"].create({"name": "Mail UX partner 2"})
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.user)
            .with_context(default_model="res.partner", default_res_ids=partners.ids)
            .create({"body": "<p>Mass</p>", "subject": "Mass", "composition_mode": "mass_mail"})
        )
        composer._action_send_mail()
        self.assertFalse(
            self.env["mail.scheduled.message"].search([("model", "=", "res.partner"), ("res_id", "in", partners.ids)])
        )

    def test_scheduled_message_adds_role_partners(self):
        role = self.env["res.role"].create({"name": "Mail UX role"})
        self.user.role_ids = role
        scheduled = self.env["mail.scheduled.message"].create(
            {
                "author_id": self.env.user.partner_id.id,
                "body": "<p>For the role</p>",
                "model": "res.partner",
                "res_id": self.partner.id,
                "scheduled_date": fields.Datetime.now() + timedelta(hours=1),
                "notification_parameters": json.dumps({"role_ids": role.ids}),
            }
        )
        scheduled._post_message()
        self.assertIn(self.user.partner_id, self.partner.message_ids[0].partner_ids)

    def test_scheduled_message_resolves_recipient_emails(self):
        cc_partner = self.env["res.partner"].create({"name": "Mail UX cc", "email": "cc@example.com"})
        self.partner.email = "to@example.com"
        scheduled = (
            self.env["mail.scheduled.message"]
            .with_user(self.user)
            .create(
                {
                    "author_id": self.user.partner_id.id,
                    "body": "<p>With recipients</p>",
                    "model": "res.partner",
                    "res_id": self.partner.id,
                    "scheduled_date": fields.Datetime.now() + timedelta(hours=1),
                    "notification_parameters": json.dumps(
                        {"partner_emails": ["to@example.com"], "partner_cc_emails": ["cc@example.com"]}
                    ),
                }
            )
        )
        scheduled._post_message()
        message = self.partner.message_ids[0]
        self.assertIn(self.partner, message.partner_ids)
        self.assertIn(cc_partner, message.partner_cc_ids)

    def test_send_test_mail_through_wizard(self):
        admin = new_test_user(self.env, login="mail_ux_admin", groups="base.group_user,base.group_system")
        server = self.env["ir.mail_server"].create({"name": "Test server", "smtp_host": "smtp.example.com"})
        wizard = (
            self.env["mail.server.test.wizard"]
            .with_user(admin)
            .create({"mail_server_id": server.id, "email_to": "to@example.com"})
        )
        smtp = MagicMock()
        with patch.object(type(self.env["ir.mail_server"]), "_connect__", return_value=smtp):
            action = wizard.action_send_test_mail()
        smtp.send_message.assert_called_once()
        self.assertEqual(action["tag"], "display_notification")
