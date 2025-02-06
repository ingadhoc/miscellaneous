# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    employee_overtime = fields.Float(
        related="employee_id.total_overtime", groups="base.group_user,portal_holidays.group_portal_backend_holiday"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Allows portal holidays users to create allocation records
        and ensures proper follower subscriptions.
        """
        if self.env.user.has_group("portal_holidays.group_portal_backend_holiday"):
            self = self.sudo()

        return super(HolidaysAllocation, self).create(vals_list)  # , self.with_context(mail_create_nosubscribe=True)
