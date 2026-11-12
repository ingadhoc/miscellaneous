from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    total_timesheet_time = fields.Integer(
        groups="hr_timesheet.group_hr_timesheet_user,portal_timesheet.group_portal_backend_timesheet"
    )


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _has_field_access(self, field, operation):
        # The timesheet grid filters tasks by is_timeoff_task, a field restricted to timesheet users.
        if (
            field.name == "is_timeoff_task"
            and operation == "read"
            and self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet")
        ):
            return True
        return super()._has_field_access(field, operation)
