# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    # Same extension the module already applies to hr.leave.allocation: the
    # core field (hr_holidays_attendance) is restricted to base.group_user,
    # but this module exposes the leave form to its portal backend group, so
    # the view element that depends on employee_overtime would be visible to
    # a group that cannot read the field (Odoo 19 flags it as an access
    # rights inconsistency on every view validation).
    employee_overtime = fields.Float(groups="base.group_user,portal_holidays.group_portal_backend_holiday")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Allows users in the portal holidays group to create leave requests
        only for themselves. If the user passes the check, the method runs with
        elevated privileges to bypass access restrictions if necessary.
        """
        if self.env.user.has_group("portal_holidays.group_portal_backend_holiday"):
            user_employee_id = self.env.user.employee_id.id
            for vals in vals_list:
                if vals.get("employee_id", user_employee_id) != user_employee_id:
                    raise AccessError(_("You can only create time off requests for yourself."))
            self = self.sudo()

        return super().create(vals_list)
