##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPortalTimesheetAttendance(TransactionCase):
    def test_portal_user_reads_attendances(self):
        """Portal backend users with Timesheets read attendances; without the group they do not."""
        Users = self.env["res.users"].with_context(no_reset_password=True)
        user = Users.create({"name": "pta_user", "login": "pta_user", "access_type": "portal_backend"})
        user.group_ids = [(4, self.env.ref("portal_timesheet.group_portal_backend_timesheet").id)]
        user_no_group = Users.create({"name": "pta_no_group", "login": "pta_no_group", "access_type": "portal_backend"})
        employee = self.env["hr.employee"].create({"name": "pta_user", "user_id": user.id})
        attendance = self.env["hr.attendance"].create({"employee_id": employee.id, "check_in": fields.Datetime.now()})
        attendance.with_user(user).check_access("read")
        self.assertEqual(self.env["hr.attendance"].with_user(user).search([("id", "=", attendance.id)]), attendance)
        with self.assertRaises(AccessError):
            attendance.with_user(user_no_group).check_access("read")
