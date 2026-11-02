from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestFieldEdgeSecurity(TransactionCase):
    """`res.partner.function` stands in for a sensitive field: the module is
    generic, so any field with `edge_groups` behaves the same."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="edge_user", groups="base.group_user")
        cls.partner = cls.env["res.partner"].create({"name": "Edge", "function": "CFO"})
        # The attribute does not exist on the field, so it is set and removed
        # by hand: mock.patch.object refuses to patch what is not there.
        field = cls.env["res.partner"]._fields["function"]
        field.edge_groups = "base.group_system"
        cls.addClassCleanup(cls.env.registry.clear_cache)
        cls.addClassCleanup(delattr, field, "edge_groups")
        cls.env.registry.clear_cache()
        cls.restricted = cls.partner.with_user(cls.user)

    def test_read_comes_back_empty(self):
        self.assertFalse(self.restricted.read(["function"])[0]["function"])
        self.assertFalse(self.restricted.search_read([("id", "=", self.partner.id)], ["function"])[0]["function"])

    def test_fields_get_does_not_announce_it(self):
        """What a client cannot read it should not discover either: this is
        what keeps the field out of the AI tools and the export dialog."""
        self.assertNotIn("function", self.restricted.fields_get(allfields=["function"]))

    def test_export_is_refused(self):
        with self.assertRaises(AccessError):
            self.restricted.export_data(["function"])

    def test_domain_is_refused(self):
        """Filtering is an oracle: it answers about the value without reading it."""
        with self.assertRaises(AccessError):
            self.restricted.search([("function", "=", "CFO")])

    def test_order_is_refused(self):
        with self.assertRaises(AccessError):
            self.restricted.search([], order="function desc")

    def test_aggregate_is_refused(self):
        with self.assertRaises(AccessError):
            self.restricted._read_group([], [], ["function:count_distinct"])

    def test_having_is_refused(self):
        """The aggregate spec carries a ':', so the check has to split on it as
        well as on '.': `having` is an oracle like the domain."""
        with self.assertRaises(AccessError):
            self.restricted._read_group([], ["id"], ["id:count"], [("function:count_distinct", ">", 0)])

    def test_the_orm_still_reads_it(self):
        """The point of closing the edge instead of the field: the server goes
        on reading it with this very user, so the business logic keeps working.
        `groups=` is what breaks here."""
        self.assertEqual(self.restricted.function, "CFO")

    def test_a_user_in_the_group_sees_it(self):
        self.user.group_ids = [(4, self.env.ref("base.group_system").id)]
        self.env.registry.clear_cache()
        self.assertEqual(self.restricted.read(["function"])[0]["function"], "CFO")

    def test_the_superuser_sees_it(self):
        self.assertEqual(self.restricted.sudo().read(["function"])[0]["function"], "CFO")

    def test_an_undeclared_field_is_untouched(self):
        self.assertEqual(self.restricted.read(["name"])[0]["name"], "Edge")
        self.assertTrue(self.restricted.search([("name", "=", "Edge")]))
