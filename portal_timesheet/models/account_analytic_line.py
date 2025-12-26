# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model
    def _get_favorite_project_id(self, employee_id=False):
        # Esto lo bypasseamos porque desde v18 trae predeterminadamente un proyecto interno que el usuario no tiene acceso
        if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            self = self.sudo()
        return super()._get_favorite_project_id(employee_id=employee_id)

    def _compute_readonly_timesheet(self):
        # let portal users with portal_timesheet access to change project in timesheets
        if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            self.readonly_timesheet = False
        else:
            super()._compute_readonly_timesheet()

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            return super(AccountAnalyticLine, self.sudo()).create(vals_list)
        return super().create(vals_list)
