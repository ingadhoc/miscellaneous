from odoo import models


class User(models.Model):
    _inherit = ["res.users"]

    def get_last_validated_timesheet_date(self):
        if not self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
            return super().get_last_validated_timesheet_date()
        else:
            return self.sudo().employee_id.last_validated_timesheet_date
