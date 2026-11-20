from datetime import timedelta

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import TransactionCase, tagged

from ..hooks import post_init_hook


@tagged("post_install", "-at_install")
class TestGoogleCalendarUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("google_calendar_sync_paused", False)
        cls.disconnected = mail_new_test_user(cls.env, login="gcal_disconnected")
        cls.connected = mail_new_test_user(cls.env, login="gcal_connected")
        cls.env["res.users.settings"]._find_or_create_for_user(cls.connected).sudo().google_calendar_rtoken = "rtoken"

    def _event(self, user, google_id="gid", need_sync=False, attendee=None):
        start = fields.Datetime.now() + timedelta(days=2)
        partners = user.partner_id | (attendee.partner_id if attendee else self.env["res.partner"])
        event = (
            self.env["calendar.event"]
            .with_context(no_calendar_sync=True)
            .create(
                {
                    "name": "Resync test",
                    "start": start,
                    "stop": start + timedelta(hours=1),
                    "user_id": user.id,
                    "partner_ids": [fields.Command.set(partners.ids)],
                    "google_id": google_id,
                }
            )
        )
        event.with_context(no_calendar_sync=True).need_sync = need_sync
        return event

    def test_restart_without_token_marks_nothing(self):
        event = self._event(self.disconnected)
        self.disconnected.sudo().google_synchronization_stopped = True
        queued = len(self.env.cr.postcommit._funcs)

        self.disconnected.with_user(self.disconnected).restart_google_synchronization()

        self.assertFalse(event.need_sync)
        self.assertFalse(self.disconnected.sudo().google_synchronization_stopped)
        self.assertEqual(len(self.env.cr.postcommit._funcs), queued)

    def test_restart_with_token_is_standard(self):
        event = self._event(self.connected)

        self.connected.with_user(self.connected).restart_google_synchronization()

        self.assertTrue(event.need_sync)

    def test_post_init_hook_resets_disconnected_users_only(self):
        settings = self.env["res.users.settings"]._find_or_create_for_user(self.disconnected).sudo()
        settings.google_calendar_sync_token = "sync-token"
        stale = self._event(self.disconnected, need_sync=True)
        not_in_google = self._event(self.disconnected, google_id=False, need_sync=True)
        other_organizer = self._event(self.connected, google_id="gid-2", need_sync=True, attendee=self.disconnected)

        post_init_hook(self.env)

        self.assertFalse(stale.need_sync)
        self.assertTrue(not_in_google.need_sync)
        self.assertTrue(other_organizer.need_sync)
        self.assertFalse(settings.google_calendar_sync_token)
        self.assertEqual(
            self.env["res.users.settings"]._find_or_create_for_user(self.connected).sudo().google_calendar_rtoken,
            "rtoken",
        )
