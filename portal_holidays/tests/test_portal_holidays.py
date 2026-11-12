from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPortalHolidays(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(
            cls.env,
            login="portal_holidays_user",
            groups="portal_holidays.group_portal_backend_holiday",
        )
        cls.own_employee = cls.env["hr.employee"].create(
            {"name": "Portal Holidays Employee", "user_id": cls.portal_user.id}
        )
        cls.other_employee = cls.env["hr.employee"].create({"name": "Other Employee"})
        cls.leave_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Portal Holidays Leave",
                "code": "PORTAL_HOLIDAYS_LEAVE",
                "count_as": "absence",
                "requires_allocation": False,
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )
        cls.allocation_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Portal Holidays Allocation",
                "code": "PORTAL_HOLIDAYS_ALLOCATION",
                "count_as": "absence",
                "requires_allocation": True,
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )
        start = fields.Date.today() + relativedelta(weeks=2, weekday=0)
        cls.vals_by_model = {
            "hr.leave": {
                "work_entry_type_id": cls.leave_type.id,
                "request_date_from": start,
                "request_date_to": start + relativedelta(days=1),
            },
            "hr.leave.allocation": {
                "work_entry_type_id": cls.allocation_type.id,
                "number_of_days": 2,
                "date_from": fields.Date.today(),
            },
        }

    def test_portal_user_requests_only_for_own_employee(self):
        """A portal backend holidays user creates time off requests and
        allocations for their own employee, and never for another one."""
        for model, vals in self.vals_by_model.items():
            records = self.env[model].with_user(self.portal_user)
            with self.subTest(f"{model}: request for own employee"):
                record = records.create({**vals, "employee_id": self.own_employee.id})
                self.assertEqual(record.employee_id, self.own_employee)
                self.assertEqual(record.create_uid, self.portal_user)
            with self.subTest(f"{model}: request for another employee is refused"):
                count = self.env[model].search_count([("employee_id", "=", self.other_employee.id)])
                with self.assertRaises(AccessError):
                    records.create({**vals, "employee_id": self.other_employee.id})
                self.assertEqual(
                    self.env[model].search_count([("employee_id", "=", self.other_employee.id)]),
                    count,
                )

    def test_portal_user_only_reaches_coworkers_through_overview(self):
        """A portal backend holidays user can neither read nor modify the time
        off and allocations of another employee, but sees them in the overview
        report, without the time off type."""
        other_leave = self.env["hr.leave"].create(
            {**self.vals_by_model["hr.leave"], "employee_id": self.other_employee.id}
        )
        other_allocation = self.env["hr.leave.allocation"].create(
            {**self.vals_by_model["hr.leave.allocation"], "employee_id": self.other_employee.id}
        )
        self.env.flush_all()
        for record in (other_leave, other_allocation):
            records = self.env[record._name].with_user(self.portal_user)
            with self.subTest(f"{record._name}: another employee's records are not readable"):
                self.assertFalse(records.search([("employee_id", "=", self.other_employee.id)]))
                with self.assertRaises(AccessError):
                    records.browse(record.id).read(["name"])
        with self.subTest("hr.leave.allocation: another employee's pending allocation cannot be modified"):
            self.assertEqual(other_allocation.state, "confirm")
            with self.assertRaises(AccessError):
                other_allocation.with_user(self.portal_user).write({"number_of_days": 50})
            self.assertEqual(other_allocation.number_of_days, 2)
        with self.subTest("overview shows the coworker's time off without its type"):
            report = self.env["hr.leave.report.calendar"].with_user(self.portal_user)
            row = report.search([("employee_id", "=", self.other_employee.id)])
            self.assertEqual(row.id, other_leave.id)
            self.assertIn(self.other_employee.name, row.display_name)
            self.assertNotIn(self.leave_type.name, row.display_name)
            with self.assertRaises(AccessError):
                row.read(["work_entry_type_id"])
