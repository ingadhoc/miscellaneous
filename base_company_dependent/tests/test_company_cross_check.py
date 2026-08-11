##############################################################################
#
#    Copyright (C) 2024  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestCompanyCrossCheck(TransactionCase):
    """End-to-end coverage for the cross-company protection on
    company_dependent Many2one fields, through load().

    The check lives exclusively in load() — the entry point for UI imports
    and module CSV data — so write()/create() are intentionally unchecked.

    Uses a transient ``company.dependent.tester`` model (registered only for
    this run, rolled back by TransactionCase) so the protection is exercised
    without depending on ``account``.
    """

    MODEL = "company.dependent.tester"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._register_test_model()

        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "E2E Company B"})
        cls.test_actor = cls.env.ref("base.user_admin")

        cls.partner_a = cls.env["res.partner"].create({"name": "E2E Partner A", "company_id": cls.company_a.id})
        cls.partner_b = cls.env["res.partner"].create({"name": "E2E Partner B", "company_id": cls.company_b.id})
        cls.partner_shared = cls.env["res.partner"].create({"name": "E2E Shared Partner", "company_id": False})

    @classmethod
    def _register_test_model(cls):
        from odoo.orm.model_classes import add_to_registry

        from . import company_dependent_models

        add_to_registry(cls.registry, company_dependent_models.CompanyDependentTester)
        cls.registry._setup_models__(cls.env.cr, [cls.MODEL])
        cls.registry.init_models(cls.env.cr, [cls.MODEL], {"models_to_check": True})
        cls.addClassCleanup(cls.registry.__delitem__, cls.MODEL)
        # Group-less ACL so the non-superuser test actor can operate the model.
        cls.env["ir.model"]._reflect_models([cls.MODEL])
        cls.env["ir.model.access"].create(
            {
                "name": "company_dependent_tester_test",
                "model_id": cls.env["ir.model"]._get(cls.MODEL).id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
        )

    def _env_a(self):
        ctx = dict(self.env.context, allowed_company_ids=[self.company_a.id])
        return self.env(user=self.test_actor, context=ctx)

    def _load(self, env, partner):
        """Helper: import a single row via load() into company.dependent.tester."""
        return env[self.MODEL].load(
            ["name", "partner_id/.id"],
            [["Tester", str(partner.id)]],
        )

    def test_load_cross_company_raises(self):
        """load() with a cross-company value raises ValidationError."""
        with self.assertRaises(ValidationError):
            self._load(self._env_a(), self.partner_b)

    def test_load_own_company_passes(self):
        """load() with an own-company value succeeds and returns an id."""
        result = self._load(self._env_a(), self.partner_a)
        self.assertTrue(result.get("ids"), "Expected a created record id")

    def test_load_company_id_false_never_blocked(self):
        """load() with a shared value (company_id=False) is never blocked."""
        result = self._load(self._env_a(), self.partner_shared)
        self.assertTrue(result.get("ids"))

    def test_load_non_company_dependent_field_ignored(self):
        """load() on a regular (non company_dependent) Many2one is never checked."""
        env = self._env_a()
        result = env[self.MODEL].load(
            ["name", "partner_regular_id/.id"],
            [["Tester", str(self.partner_b.id)]],
        )
        self.assertTrue(result.get("ids"))

    def test_load_comodel_without_company_field(self):
        """load() skips a company_dependent Many2one to a comodel without company."""
        result = self._env_a()[self.MODEL].load(
            ["name", "currency_id/.id"],
            [["Tester", str(self.env.ref("base.USD").id)]],
        )
        self.assertTrue(result.get("ids"))

    def test_sibling_branch_domain_behavior_documented(self):
        """Lock the sibling-branch behavior, whatever _check_company_domain does.

        Standard Odoo excludes a sibling branch's records from the domain, so
        the guard raises. A branch-aware override would make them visible and
        the guard would pass. The test asserts whichever holds, catching a shift.
        """
        branch_1 = self.env["res.company"].create({"name": "Sibling Branch 1", "parent_id": self.company_a.id})
        branch_2 = self.env["res.company"].create({"name": "Sibling Branch 2", "parent_id": self.company_a.id})
        partner_of_branch_2 = self.env["res.partner"].create({"name": "Partner of Branch 2", "company_id": branch_2.id})
        self.test_actor.sudo().write({"company_ids": [(4, branch_1.id), (4, branch_2.id)]})
        ctx = dict(self.env.context, allowed_company_ids=[branch_1.id])
        env_branch_1 = self.env(user=self.test_actor, context=ctx)

        company_domain = self.env["res.partner"]._check_company_domain(branch_1)
        sibling_accessible = bool(
            self.env["res.partner"]
            .sudo()
            .with_context(active_test=False)
            .search(company_domain + [("id", "=", partner_of_branch_2.id)], limit=1)
        )

        if sibling_accessible:
            result = self._load(env_branch_1, partner_of_branch_2)
            self.assertTrue(result.get("ids"))
        else:
            with self.assertRaises(ValidationError):
                self._load(env_branch_1, partner_of_branch_2)
