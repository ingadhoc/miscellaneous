from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def restart_google_synchronization(self):
        self.ensure_one()
        if self.sudo().google_calendar_rtoken:
            return super().restart_google_synchronization()
        # Without a token nothing can be sent, and events edited while disconnected
        # are already marked: marking every event only delays the redirect to Google.
        self.sudo().google_synchronization_stopped = False
