from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    total_timesheet_time = fields.Integer(
        groups="hr_timesheet.group_hr_timesheet_user,portal_timesheet.group_portal_backend_timesheet"
    )
