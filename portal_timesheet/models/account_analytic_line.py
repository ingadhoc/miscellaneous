# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,models

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'


    @api.model
    def _get_favorite_project_id(self, employee_id=False):
        if self.env.user.has_group('portal_timesheet.group_portal_backend_timesheet'):
            self = self.sudo()
        return super()._get_favorite_project_id(employee_id=employee_id)
