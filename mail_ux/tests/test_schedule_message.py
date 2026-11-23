import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestScheduleMessage(TransactionCase):
    def test_send_context_without_private_keys(self):
        """send_context is a Json field: a private key holding recordsets
        (base_automation's __action_done) makes the insert fail."""
        self.env.user.send_message_delay = 60
        partner = self.env["res.partner"].create({"name": "Test Schedule"})
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                **{
                    "__action_done": {self.env.user: partner},
                    "lang": "en_US",
                }
            )
            .create(
                {
                    "model": "res.partner",
                    "res_ids": repr(partner.ids),
                    "subject": "Test",
                    "body": "<p>Test</p>",
                }
            )
        )

        composer._action_send_mail()

        scheduled = self.env["mail.scheduled.message"].search(
            [("model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled.send_context, {"lang": "en_US"})

    def test_delay_keeps_composer_scheduled_date(self):
        """A date set on the composer (or by its template) is not replaced by the user delay."""
        self.env.user.send_message_delay = 60
        partner = self.env["res.partner"].create({"name": "Test Schedule"})
        planned = fields.Datetime.now().replace(microsecond=0) + timedelta(days=2)
        composer = self.env["mail.compose.message"].create(
            {
                "model": "res.partner",
                "res_ids": repr(partner.ids),
                "body": "<p>Later</p>",
                "scheduled_date": fields.Datetime.to_string(planned),
            }
        )
        composer._action_send_mail()
        scheduled = self.env["mail.scheduled.message"].search(
            [("model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertEqual(scheduled.scheduled_date, planned)

    def test_mass_mail_with_delay_is_not_scheduled(self):
        """Scheduling only works in mono-comment mode: mass mail sends the emails with the delay."""
        self.env.user.send_message_delay = 60
        partners = self.env["res.partner"].create(
            [{"name": "Mass 1", "email": "mass1@example.com"}, {"name": "Mass 2", "email": "mass2@example.com"}]
        )
        composer = self.env["mail.compose.message"].create(
            {
                "model": "res.partner",
                "res_ids": repr(partners.ids),
                "body": "<p>Mass</p>",
                "subject": "Mass",
                "composition_mode": "mass_mail",
            }
        )
        composer._action_send_mail()
        self.assertFalse(
            self.env["mail.scheduled.message"].search([("model", "=", "res.partner"), ("res_id", "in", partners.ids)])
        )
        mails = self.env["mail.mail"].search([("model", "=", "res.partner"), ("res_id", "in", partners.ids)])
        self.assertEqual(len(mails), 2)
        self.assertTrue(all(mail.scheduled_date > fields.Datetime.now() for mail in mails))

    def test_scheduled_message_resolves_recipient_emails(self):
        """Recipients the chatter sends only by email are notified when the message is posted."""
        partner = self.env["res.partner"].create({"name": "Test Schedule", "email": "to@example.com"})
        scheduled = self.env["mail.scheduled.message"].create(
            {
                "author_id": self.env.user.partner_id.id,
                "body": "<p>With recipients</p>",
                "model": "res.partner",
                "res_id": partner.id,
                "scheduled_date": fields.Datetime.now() + timedelta(hours=1),
                "notification_parameters": json.dumps({"partner_emails": ["to@example.com"]}),
            }
        )
        scheduled._post_message()
        self.assertIn(partner, partner.message_ids[0].partner_ids)
