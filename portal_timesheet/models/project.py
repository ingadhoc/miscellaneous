from odoo import models, fields


class Project(models.Model):
    _inherit = "project.project"

    total_timesheet_time = fields.Integer(
        groups='hr_timesheet.group_hr_timesheet_user, portal_timesheet.group_portal_backend_timesheet')

class Task(models.Model):
    _inherit = "project.task"

    def _ensure_fields_are_accessible(self, fields, operation='read', check_group_user=True):
        if not self.env.user.has_group('portal_timesheet.group_portal_backend_timesheet'):
            super()._ensure_fields_are_accessible(fields, operation, check_group_user)
