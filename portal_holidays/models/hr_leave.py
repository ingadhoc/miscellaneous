# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import AccessError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

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
