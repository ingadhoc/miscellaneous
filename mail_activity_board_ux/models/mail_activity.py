# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def open_activity_dashboard_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.id,
            'context': dict(self._context),
        }
