##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestPortalWizard(TransactionCase):
    def test_action_grant_access_all(self):
        partner_model = self.env["res.partner"].sudo()
        valid_partner_1 = partner_model.create({"name": "Valid Contact 1", "email": "valid1@test.example.com"})
        valid_partner_2 = partner_model.create({"name": "Valid Contact 2", "email": "valid2@test.example.com"})
        invalid_partner = partner_model.create({"name": "Invalid Contact", "email": "not-an-email"})

        partners = valid_partner_1 + valid_partner_2 + invalid_partner
        wizard = self.env["portal.wizard"].with_context(active_ids=partners.ids).create({})
        self.assertEqual(len(wizard.user_ids), 3)

        wizard.action_grant_access_all()

        group_portal = self.env.ref("base.group_portal")
        for partner in (valid_partner_1, valid_partner_2):
            self.assertTrue(partner.user_ids, "A portal user should have been created")
            self.assertIn(group_portal, partner.user_ids.group_ids)

        self.assertFalse(
            invalid_partner.user_ids,
            "No user should be created for a contact with an invalid email",
        )

    def test_action_grant_access_all_skips_existing_portal_user(self):
        partner_model = self.env["res.partner"].sudo()
        already_portal_partner = partner_model.create(
            {"name": "Already Portal Contact", "email": "already@test.example.com"}
        )
        wizard = self.env["portal.wizard"].with_context(active_ids=already_portal_partner.ids).create({})
        wizard.user_ids.action_grant_access()
        user = already_portal_partner.user_ids
        self.assertTrue(user, "Precondition: partner should already have a portal user")

        # Re-open the wizard: the existing portal user must be skipped, not re-processed.
        wizard_2 = self.env["portal.wizard"].with_context(active_ids=already_portal_partner.ids).create({})
        wizard_2.action_grant_access_all()

        self.assertEqual(already_portal_partner.user_ids, user)
