# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def open_activity_dashboard_form(self):
        view_id = self.env.ref('mail_activity_board.mail_activity_view_form_board').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'current',
            'res_id': self.id,
            'context': dict(self._context),
        }
