from odoo import models, _
from odoo.exceptions import UserError

class User(models.Model):
    _inherit = ['res.users']


    def get_last_validated_timesheet_date(self):
        if not self.user_has_groups('portal_timesheet.group_portal_backend_timesheet'):
            return super().get_last_validated_timesheet_date()
        else:
            return self.sudo().employee_id.last_validated_timesheet_date

