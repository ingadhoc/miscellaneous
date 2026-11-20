from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def restart_google_synchronization(self):
        self.ensure_one()
        if not self.sudo().google_calendar_rtoken:
            # Without a token the first sync is a full sync: it already takes every
            # event in range, so marking them only delays the redirect to Google.
            self.sudo().google_synchronization_stopped = False
            return
        # Keep the marks but do not queue one Google patch per event in this request:
        # sync_data and the cron send them in batches of 200.
        return super(ResUsers, self.with_context(no_calendar_sync=True)).restart_google_synchronization()
