# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    employee_overtime = fields.Float(
        related="employee_id.total_overtime", groups="base.group_user,portal_holidays.group_portal_backend_holiday"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Allows users in the portal holidays group to create allocation records
        only for themselves. If the user passes the check, the method runs with
        elevated privileges to bypass access restrictions if necessary.
        """
        if self.env.user.has_group("portal_holidays.group_portal_backend_holiday"):
            user_employee_id = self.env.user.employee_id.id
            for vals in vals_list:
                if vals.get("employee_id") != user_employee_id:
                    raise AccessError(_("You can only create allocations for yourself."))
            self = self.sudo()

        return super().create(vals_list)
