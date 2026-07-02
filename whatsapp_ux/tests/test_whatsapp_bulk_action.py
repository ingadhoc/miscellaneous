##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.whatsapp.tests.common import WhatsAppCase
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWhatsAppBulkAction(TransactionCase, WhatsAppCase):
    """Self-contained: builds its own WhatsApp account/templates instead of the
    heavier WhatsAppCommon bootstrap, and reuses WhatsAppCase only for the API
    mock and assert helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.channel_model = cls.env["ir.model"]._get("discuss.channel")

        # A whatsapp.account requires at least one internal (non-share) user in
        # notify_user_ids, so create a dedicated one.
        cls.wa_notify_user = cls.env["res.users"].create(
            {
                "name": "WA UX Notify",
                "login": "wa_ux_notify",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.wa_account = cls.env["whatsapp.account"].create(
            {
                "name": "UX Test Account",
                "account_uid": "ux_account_uid",
                "app_secret": "ux_app_secret",
                "app_uid": "ux_app_uid",
                "phone_uid": "ux_phone_uid",
                "token": "ux_token",
                "notify_user_ids": [(6, 0, cls.wa_notify_user.ids)],
            }
        )

        # An approved template on res.partner (plain body, no report -> no PDF).
        cls.partner_template = cls.env["whatsapp.template"].create(
            {
                "name": "UX Partner",
                "template_name": "ux_partner_template",
                "body": "Hi there.",
                "status": "approved",
                "model_id": cls.partner_model.id,
                "phone_field": "phone",
                "wa_account_id": cls.wa_account.id,
                "wa_template_uid": "ux_partner_template",
            }
        )
        # A second approved template on a *different* model proves the mechanism
        # is generic and not tied to a single model.
        cls.channel_template = cls.env["whatsapp.template"].create(
            {
                "name": "UX Channel",
                "template_name": "ux_channel_template",
                "body": "Hi channel.",
                "status": "approved",
                "model_id": cls.channel_model.id,
                "phone_field": "whatsapp_number",
                "wa_account_id": cls.wa_account.id,
                "wa_template_uid": "ux_channel_template",
            }
        )
        # Recipients with a phone number for the bulk-send run.
        india = cls.env.ref("base.in")
        cls.partner_1 = cls.env["res.partner"].create(
            {"name": "Wa Customer One", "country_id": india.id, "phone": "+91 12345 67891"}
        )
        cls.partner_2 = cls.env["res.partner"].create(
            {"name": "Wa Customer Two", "country_id": india.id, "phone": "+91 12345 90000"}
        )
        cls.partners = cls.partner_1 + cls.partner_2

    def test_action_created_on_approval(self):
        """An approved template gets a bulk send server action bound to its
        model's list view."""
        action = self.partner_template._get_bulk_send_action()
        self.assertTrue(action, "Approved template should get a bulk send action")
        self.assertEqual(action.state, "whatsapp")
        self.assertEqual(action.wa_template_id, self.partner_template)
        self.assertEqual(action.binding_model_id, self.partner_model)
        self.assertEqual(action.binding_view_types, "list")

    def test_generic_multi_model(self):
        """The mechanism is generic: a template on another model gets its own
        action, bound to that model."""
        action = self.channel_template._get_bulk_send_action()
        self.assertTrue(action)
        self.assertEqual(action.binding_model_id, self.channel_model)
        # Each model/template pair has its own dedicated action.
        self.assertNotEqual(action, self.partner_template._get_bulk_send_action())

    def test_run_bulk_send_queues_messages(self):
        """Running the action over several records queues one whatsapp.message
        per record, reusing the native batch/cron dispatch."""
        action = self.partner_template._get_bulk_send_action()
        with self.mockWhatsappGateway():
            action.with_context(
                active_model="res.partner",
                active_ids=self.partners.ids,
            ).run()
        for partner in self.partners:
            self.assertWAMessageFromRecord(partner, status="outgoing")

    def test_toggle_optout_removes_action(self):
        """Opting out (bulk_send_action=False) removes the action."""
        self.assertTrue(self.partner_template._get_bulk_send_action())
        self.partner_template.bulk_send_action = False
        self.assertFalse(self.partner_template._get_bulk_send_action())

    def test_unapprove_removes_action(self):
        """A template that is no longer approved loses its action."""
        self.assertTrue(self.partner_template._get_bulk_send_action())
        self.partner_template.status = "draft"
        self.assertFalse(self.partner_template._get_bulk_send_action())

    def test_unlink_template(self):
        """Deleting a template does not fail despite the restrict ondelete on
        ir.actions.server.wa_template_id (our action is removed first)."""
        template = self.env["whatsapp.template"].create(
            {
                "name": "UX Throwaway",
                "template_name": "ux_throwaway_template",
                "body": "Hi.",
                "status": "approved",
                "model_id": self.partner_model.id,
                "phone_field": "phone",
                "wa_account_id": self.wa_account.id,
                "wa_template_uid": "ux_throwaway_template",
            }
        )
        action = template._get_bulk_send_action()
        self.assertTrue(action)
        template.unlink()
        self.assertFalse(action.exists())
