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
