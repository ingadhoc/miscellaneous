##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase


class TestMailActivityQuickBadges(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param("base_ux.activity_quick_badges", "2")
        cls.quick_types = cls.env["mail.activity.type"].create(
            [
                {"name": "Test quick 1", "sequence": -20},
                {"name": "Test quick 2", "sequence": -19},
            ]
        )
        cls.other_type = cls.env["mail.activity.type"].create({"name": "Test not quick", "sequence": 999})
        cls.partner_model_id = cls.env["ir.model"]._get_id("res.partner")
        cls.partner = cls.env["res.partner"].create({"name": "Test activity quick badges"})

    def test_quick_types_limited_by_parameter(self):
        self.assertEqual(self.env["mail.activity.type"]._get_quick_activity_types(), self.quick_types)

    def test_schedule_wizard_shows_only_quick_types(self):
        wizard = self.env["mail.activity.schedule"].create(
            {
                "res_model_id": self.partner_model_id,
                "res_model": "res.partner",
                "res_ids": str(self.partner.ids),
            }
        )
        self.assertEqual(wizard.quick_activity_ids, self.quick_types)

    def test_existing_activity_keeps_its_own_type(self):
        """When editing an activity whose type is not among the quick ones, that type must
        still be offered as a badge, otherwise the stored value is not rendered at all."""
        activity = self.env["mail.activity"].create(
            {
                "res_model_id": self.partner_model_id,
                "res_id": self.partner.id,
                "activity_type_id": self.other_type.id,
                "summary": "test",
            }
        )
        self.assertEqual(activity.quick_activity_ids, self.quick_types | self.other_type)
