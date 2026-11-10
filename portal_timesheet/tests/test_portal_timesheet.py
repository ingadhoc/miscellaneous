##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPortalTimesheet(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.group_timesheet = cls.env.ref("portal_timesheet.group_portal_backend_timesheet")
        cls.user = Users.create({"name": "pt_user", "login": "pt_user", "access_type": "portal_backend"})
        cls.user.group_ids = [(4, cls.group_timesheet.id)]
        cls.user_no_group = Users.create(
            {"name": "pt_no_group", "login": "pt_no_group", "access_type": "portal_backend"}
        )
        cls.employee = cls.env["hr.employee"].create({"name": "pt_user", "user_id": cls.user.id})
        cls.project = cls.env["project.project"].create({"name": "Followed", "privacy_visibility": "portal"})
        cls.project.message_subscribe(partner_ids=cls.user.partner_id.ids)
        cls.other_project = cls.env["project.project"].create({"name": "Not followed", "privacy_visibility": "portal"})
        cls.task = cls.env["project.task"].create({"name": "Followed task", "project_id": cls.project.id})
        cls.other_task = cls.env["project.task"].create({"name": "Other task", "project_id": cls.other_project.id})
        cls.other_line = cls.env["account.analytic.line"].create(
            {
                "name": "Other hours",
                "project_id": cls.other_project.id,
                "task_id": cls.other_task.id,
                "employee_id": cls.env["hr.employee"].create({"name": "other"}).id,
                "unit_amount": 2,
            }
        )

    def test_portal_user_logs_hours_on_followed_project(self):
        """Portal backend users log hours as followers of the project, not as collaborators.

        Covers: project read limited to followed portal projects, timesheet creation on a
        followed task, no access to the timesheets of other projects, no task write, and the
        timesheet helpers that need sudo.
        """
        Project = self.env["project.project"].with_user(self.user)
        Line = self.env["account.analytic.line"].with_user(self.user)
        with self.subTest("sees the followed project and not the other one"):
            self.assertEqual(Project.search([("id", "in", (self.project | self.other_project).ids)]), self.project)
            with self.assertRaises(AccessError):
                self.other_project.with_user(self.user).check_access("read")
        with self.subTest("logs hours on a task of the followed project"):
            line = Line.create(
                {"name": "My hours", "project_id": self.project.id, "task_id": self.task.id, "unit_amount": 3}
            )
            self.assertEqual(line.employee_id, self.employee)
            self.assertEqual(Line.search([("project_id", "=", self.project.id)]), line)
            self.assertFalse(line.readonly_timesheet)
        with self.subTest("does not see the hours of the other project"):
            self.assertFalse(Line.search([("id", "=", self.other_line.id)]))
            with self.assertRaises(AccessError):
                self.other_line.with_user(self.user).check_access("read")
        with self.subTest("does not write tasks: logging hours does not need it"):
            for task in self.task | self.other_task:
                with self.assertRaises(AccessError):
                    task.with_user(self.user).check_access("write")
        with self.subTest("timesheet helpers do not raise access errors"):
            self.user.with_user(self.user).get_last_validated_timesheet_date()
            self.assertEqual(
                Line._get_favorite_project_id(self.employee.id), Line.sudo()._get_favorite_project_id(self.employee.id)
            )

    def test_portal_user_filters_tasks_by_timeoff(self):
        """The timesheet grid filters tasks by is_timeoff_task, a field restricted to timesheet users."""
        if "is_timeoff_task" not in self.env["project.task"]._fields:
            self.skipTest("project_timesheet_holidays is not installed")
        Task = self.env["project.task"].with_user(self.user)
        self.assertIn(self.task, Task.search([("is_timeoff_task", "=", False)]))
        self.assertFalse(self.task.with_user(self.user).is_timeoff_task)

    def test_timesheet_menu_visible(self):
        """The Timesheets root menu stays visible to the group: portal_backend hides root menus without group."""
        menu = self.env.ref("hr_timesheet.timesheet_menu_root")
        Menu = self.env["ir.ui.menu"]
        self.assertIn(menu.id, Menu.with_user(self.user)._visible_menu_ids())
        self.assertNotIn(menu.id, Menu.with_user(self.user_no_group)._visible_menu_ids())
