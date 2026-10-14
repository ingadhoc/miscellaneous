##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestAccessType(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_portal = cls.env.ref("base.group_portal")
        cls.group_pb = cls.env.ref("portal_backend.group_portal_backend")

    def _create(self, login, **vals):
        return self.Users.create({"name": login, "login": login, **vals})

    # -- manual create -------------------------------------------------------
    def test_create_internal(self):
        user = self._create("at_internal", access_type="internal")
        self.assertEqual(user.access_type, "internal")
        self.assertFalse(user.share)
        self.assertIn(self.group_user, user.all_group_ids)
        self.assertNotIn(self.group_portal, user.all_group_ids)

    def test_create_portal(self):
        user = self._create("at_portal", access_type="portal")
        self.assertEqual(user.access_type, "portal")
        self.assertTrue(user.share)
        self.assertIn(self.group_portal, user.all_group_ids)
        self.assertNotIn(self.group_user, user.all_group_ids)
        self.assertNotIn(self.group_pb, user.all_group_ids)

    def test_create_portal_backend(self):
        user = self._create("at_pb", access_type="portal_backend")
        self.assertEqual(user.access_type, "portal_backend")
        self.assertTrue(user.share)
        self.assertIn(self.group_pb, user.all_group_ids)
        # group_pb implies group_portal
        self.assertIn(self.group_portal, user.all_group_ids)
        self.assertNotIn(self.group_user, user.all_group_ids)

    # -- the disjoint error must never fire ----------------------------------
    def test_type_wins_over_internal_role(self):
        """access_type portal must strip an explicitly requested internal group, no error."""
        user = self._create(
            "at_conflict",
            access_type="portal",
            group_ids=[Command.link(self.group_user.id)],
        )
        self.assertEqual(user.access_type, "portal")
        self.assertTrue(user.share)
        self.assertNotIn(self.group_user, user.all_group_ids)

    def test_switch_to_portal_strips_internal_app_groups(self):
        """Groups implying group_user (e.g. Sales/Purchase from *_ux) must be dropped on switch.

        Reproduces the reported bug: such groups re-imply group_user, so the type reverted to
        Internal (and would trip the disjoint constraint on save).
        """
        app_group = self.env["res.groups"].create(
            {"name": "Test Internal App", "implied_ids": [Command.link(self.group_user.id)]}
        )
        user = self._create("at_appgrp", access_type="internal", group_ids=[Command.link(app_group.id)])
        self.assertEqual(user.access_type, "internal")
        user.access_type = "portal"
        self.assertEqual(user.access_type, "portal")  # must NOT revert to internal
        self.assertTrue(user.share)
        self.assertNotIn(app_group, user.all_group_ids)
        self.assertNotIn(self.group_user, user.all_group_ids)

    def test_portal_advanced_group_ids_inverse(self):
        """Writing the dedicated field (what the widget does) must add the group to group_ids
        and keep the user as portal_backend."""
        advanced = self.env["res.users"]._portal_advanced_groups()
        if not advanced:
            self.skipTest("No Advanced Portal groups installed (portal_holidays/timesheet absent)")
        user = self._create("at_adv", access_type="portal_backend")
        user.portal_advanced_group_ids = [Command.set(advanced[0].ids)]
        self.assertIn(advanced[0], user.group_ids)
        self.assertEqual(user.access_type, "portal_backend")
        self.assertTrue(user.share)
        # and removing it again
        user.portal_advanced_group_ids = [Command.clear()]
        self.assertNotIn(advanced[0], user.group_ids)
        self.assertEqual(user.access_type, "portal_backend")

    # -- import parity (Path A: access_type vs Path B: groups) ---------------
    def test_import_parity_portal_backend(self):
        path_a = self._create("at_imp_a", access_type="portal_backend")
        path_b = self._create("at_imp_b", group_ids=[Command.set([self.group_pb.id])])
        self.assertEqual(path_b.access_type, "portal_backend")
        self.assertEqual(path_a.share, path_b.share)
        self.assertEqual(set(path_a.all_group_ids.ids), set(path_b.all_group_ids.ids))

    def test_create_multi_mixed_batch(self):
        users = self.Users.create(
            [
                {"name": "b_int", "login": "b_int", "access_type": "internal"},
                {"name": "b_por", "login": "b_por", "access_type": "portal"},
                {"name": "b_pb", "login": "b_pb", "access_type": "portal_backend"},
            ]
        )
        by_login = {u.login: u for u in users}
        self.assertFalse(by_login["b_int"].share)
        self.assertTrue(by_login["b_por"].share)
        self.assertTrue(by_login["b_pb"].share)
        self.assertIn(self.group_pb, by_login["b_pb"].all_group_ids)

    # -- partner handling ----------------------------------------------------
    def test_partner_autocreated(self):
        user = self._create("at_partner", access_type="portal_backend")
        self.assertTrue(user.partner_id)
        self.assertEqual(user.partner_id.name, "at_partner")

    def test_partner_reused_when_provided(self):
        partner = self.env["res.partner"].create({"name": "Existing Contact"})
        user = self.Users.create({"login": "at_existing", "partner_id": partner.id, "access_type": "portal_backend"})
        self.assertEqual(user.partner_id, partner)

    def test_partner_reused_by_email_on_import(self):
        """Importing a portal user whose email matches an existing contact reuses it (no duplicate)."""
        contact = self.env["res.partner"].create({"name": "Imp Contact", "email": "imp@example.com"})
        before = self.env["res.partner"].search_count([("email", "=ilike", "imp@example.com")])
        user = self.Users.create(
            {
                "login": "imp@example.com",
                "name": "Imp Contact",
                "email": "imp@example.com",
                "access_type": "portal_backend",
            }
        )
        self.assertEqual(user.partner_id, contact)
        self.assertEqual(self.env["res.partner"].search_count([("email", "=ilike", "imp@example.com")]), before)

    def test_partner_not_reused_when_ambiguous(self):
        """Two contacts with the same email -> ambiguous -> create a fresh partner, don't guess."""
        self.env["res.partner"].create({"name": "Dup A", "email": "dup@example.com"})
        self.env["res.partner"].create({"name": "Dup B", "email": "dup@example.com"})
        user = self.Users.create(
            {"login": "dup@example.com", "name": "Dup", "email": "dup@example.com", "access_type": "portal"}
        )
        self.assertNotIn(user.partner_id.name, ("Dup A", "Dup B"))

    # -- write: changing type away from backend cleans advanced accesses -----
    def test_write_clears_advanced_when_leaving_backend(self):
        advanced = self.env["res.users"]._portal_advanced_groups()
        if not advanced:
            self.skipTest("No Advanced Portal groups installed (portal_holidays/timesheet absent)")
        user = self._create("at_leave", access_type="portal_backend")
        user.group_ids = [Command.link(advanced[0].id)]
        self.assertIn(advanced[0], user.all_group_ids)
        user.access_type = "internal"
        self.assertNotIn(advanced[0], user.group_ids)
        self.assertEqual(user.access_type, "internal")

    def test_backend_to_internal_gets_default_groups(self):
        """Coming from an external type, the user gets the groups of a new internal user (as the native Role)."""
        user = self._create("at_pb_to_internal", access_type="portal_backend")
        user.access_type = "internal"
        self.assertFalse(user.share)
        self.assertLessEqual(user._default_groups(), user.group_ids)
        self.assertNotIn(self.group_pb, user.all_group_ids)

    def test_create_internal_keeps_given_groups(self):
        """On create or import the given groups are kept: the default groups are only for a type switch."""
        self.env.ref("base.default_user_group").implied_ids = [
            Command.link(self.env.ref("base.group_partner_manager").id)
        ]
        group = self.env.ref("base.group_multi_currency")
        user = self._create("at_int_given", access_type="internal", group_ids=[Command.set(group.ids)])
        self.assertEqual(user.group_ids, group + self.group_user)
        switched = self._create("at_int_switched", access_type="portal_backend")
        switched.access_type = "internal"
        self.assertIn(self.env.ref("base.group_partner_manager"), switched.group_ids)

    def test_access_type_follows_written_groups(self):
        user = self._create("at_follow", access_type="portal")
        user.write({"group_ids": [Command.set(self.group_user.ids)]})
        self.assertEqual(user.access_type, "internal")

    def test_form_internal_then_role_user(self):
        """Switching the type and picking a Role in the same edit keeps the type (Roles shows up with 2 companies)."""
        company = self.env["res.company"].create({"name": "at_form_company"})
        user = self._create("at_form", access_type="portal_backend")
        user.write({"company_ids": [Command.link(company.id)]})
        for role in ("regular_user", "light_user", "group_system"):
            with Form(user, view="base.view_users_form") as form:
                form.access_type = "internal"
                form.role = role
            self.assertEqual(user.access_type, "internal", role)
            self.assertFalse(user.share, role)
            user.access_type = "portal_backend"
