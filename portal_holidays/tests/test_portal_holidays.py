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
