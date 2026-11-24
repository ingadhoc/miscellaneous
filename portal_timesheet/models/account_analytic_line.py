# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.fields import Domain


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _domain_project_id(self):
        domain = super()._domain_project_id()
        if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            # Sharing a project only adds collaborators, and invited users projects are offered to followers only.
            domain |= Domain(
                [
                    ("allow_timesheets", "=", True),
                    ("is_template", "=", False),
                    ("collaborator_ids.partner_id", "in", [self.env.user.partner_id.id]),
                ]
            )
        return domain

    project_id = fields.Many2one(domain=_domain_project_id)

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

    @api.onchange("product_id", "product_uom_id", "unit_amount", "currency_id")
    def on_change_unit_amount(self):
        # It reads product costs, categories and accounts, which these users cannot read.
        if not self.env.su and self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            return super(AccountAnalyticLine, self.sudo()).on_change_unit_amount()
        return super().on_change_unit_amount()

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            return super(AccountAnalyticLine, self.sudo()).create(vals_list)
        return super().create(vals_list)

    def unlink(self):
        # sale reads the sale order lines of the hours on delete, which these users cannot read.
        if not self.env.su and self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            self.check_access("unlink")
            # as superuser it would skip the check of validated timesheets
            self.check_if_allowed(delete=True)
            return super(AccountAnalyticLine, self.sudo()).unlink()
        return super().unlink()
