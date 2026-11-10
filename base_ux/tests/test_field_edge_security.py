##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..models.field_edge_security import FIELD_EDGE_SECURITY, validate_rules


@tagged("post_install", "-at_install")
class TestFieldEdgeSecurity(TransactionCase):
    """`res.partner.function` stands in for a sensitive field: the mechanism is
    generic, so any entry of the list behaves the same, and the test does not
    need the module that owns the real field to be installed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="edge_user", groups="base.group_user,base.group_allow_export")
        cls.partner = cls.env["res.partner"].create({"name": "Edge", "function": "CFO"})
        # The list is the module's own data, so the entry is added to it and
        # taken out again instead of patching a copy: both namespaces that read
        # it hold this very dict.
        FIELD_EDGE_SECURITY["res.partner"] = {"function": "base.group_system"}
        cls.addClassCleanup(cls.env.registry.clear_cache)
        cls.addClassCleanup(FIELD_EDGE_SECURITY.pop, "res.partner")
        cls.env.registry.clear_cache()
        cls.restricted = cls.partner.with_user(cls.user)

    def test_read_comes_back_empty(self):
        self.assertFalse(self.restricted.read(["function"])[0]["function"])
        self.assertFalse(self.restricted.search_read([("id", "=", self.partner.id)], ["function"])[0]["function"])

    def test_export_is_refused(self):
        with self.assertRaises(AccessError):
            self.restricted.export_data(["function"])

    def test_an_export_that_walks_a_relation_is_refused(self):
        """An export spec walks relations with '/', and the field at the end of
        the walk is as readable as a local one."""
        with self.assertRaises(AccessError):
            self.env["res.users"].with_user(self.user).browse(self.user.id).export_data(["partner_id/function"])

    def test_the_orm_still_reads_it(self):
        """The point of blanking the client paths instead of the field: the
        server goes on reading it with this very user, so the business logic
        keeps working. `groups=` is what breaks here."""
        self.assertEqual(self.restricted.function, "CFO")

    def test_a_user_in_the_group_sees_it(self):
        self.user.groups_id = [(4, self.env.ref("base.group_system").id)]
        self.env.registry.clear_cache()
        self.assertEqual(self.restricted.read(["function"])[0]["function"], "CFO")

    def test_the_superuser_sees_it(self):
        self.assertEqual(self.restricted.sudo().read(["function"])[0]["function"], "CFO")

    def test_an_undeclared_field_is_untouched(self):
        self.assertEqual(self.restricted.read(["name"])[0]["name"], "Edge")
        self.assertEqual(self.restricted.export_data(["name"])["datas"], [["Edge"]])


@tagged("post_install", "-at_install")
class TestFieldEdgeSecurityRules(TransactionCase):
    """The list itself: the format is checked when the module loads, what the
    entries name is checked here, where the modules are installed."""

    def test_every_installed_entry_resolves(self):
        """An entry whose module is not installed does nothing, by design. One
        whose module IS installed has to name a field that exists and a group
        that exists, or it is a typo that leaves the field open."""
        for model_name, fields in FIELD_EDGE_SECURITY.items():
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            for field_name, group_spec in fields.items():
                self.assertIn(
                    field_name,
                    model._fields,
                    "%s has no field %s" % (model_name, field_name),
                )
                for token in group_spec.split(","):
                    xml_id = token.strip().removeprefix("!")
                    if xml_id.split(".")[0] in self.env["ir.module.module"]._installed():
                        self.assertTrue(
                            self.env.ref(xml_id, raise_if_not_found=False),
                            "%s.%s names a group that does not exist: %s" % (model_name, field_name, xml_id),
                        )

    def test_the_format_is_enforced(self):
        """A pull request to the list that gets the format wrong has to fail
        when the module loads, not leave a field silently open."""
        for broken in (
            {"not_a_model": {"x": "base.group_user"}},
            {"res.partner": {}},
            {"res.partner": {"function": ""}},
            {"res.partner": {"function": "group_system"}},
            {"res.partner": {"function": "!base.group_system,bad"}},
        ):
            with self.assertRaises(ValueError):
                validate_rules(broken)

    def test_a_good_entry_passes(self):
        validate_rules({"res.partner": {"function": "!base.group_system,base.group_user"}})
