##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestWhatsAppLeave(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_owner = new_test_user(cls.env, login="wa_ux_owner", groups="base.group_user")
        cls.user_guard = new_test_user(cls.env, login="wa_ux_guard", groups="base.group_user")
        cls.customer = cls.env["res.partner"].create({"name": "WA UX Customer", "phone": "+5491112345678"})
        cls.wa_account = cls.env["whatsapp.account"].create(
            {
                "name": "UX Leave Account",
                "account_uid": "ux_leave_account_uid",
                "app_secret": "ux_leave_app_secret",
                "app_uid": "ux_leave_app_uid",
                "phone_uid": "ux_leave_phone_uid",
                "token": "ux_leave_token",
                "notify_user_ids": [(6, 0, cls.user_owner.ids)],
            }
        )
        # Members in this order: the owner is the first internal one, as the native guard reads it.
        cls.channel = (
            cls.env["discuss.channel"]
            .with_user(cls.user_owner)
            .create(
                {
                    "channel_type": "whatsapp",
                    "name": "WA UX Leave",
                    "wa_account_id": cls.wa_account.id,
                    "whatsapp_number": "5491112345678",
                    "whatsapp_partner_id": cls.customer.id,
                    "channel_member_ids": [
                        (0, 0, {"partner_id": cls.customer.id}),
                        (0, 0, {"partner_id": cls.user_owner.partner_id.id}),
                        (0, 0, {"partner_id": cls.user_guard.partner_id.id}),
                    ],
                }
            )
        )

    def test_store_sends_owner(self):
        result = Store().add(self.channel.with_user(self.user_guard)).get_result()
        channel_data = next(data for data in result["discuss.channel"] if data["id"] == self.channel.id)
        self.assertEqual(channel_data["whatsapp_owner_partner_id"], self.user_owner.partner_id.id)

    def test_member_can_leave(self):
        self.channel.with_user(self.user_guard).action_unfollow()
        self.assertNotIn(self.user_guard.partner_id, self.channel.channel_member_ids.partner_id)

    def test_owner_cannot_leave(self):
        self.channel.with_user(self.user_owner).action_unfollow()
        self.assertIn(self.user_owner.partner_id, self.channel.channel_member_ids.partner_id)
