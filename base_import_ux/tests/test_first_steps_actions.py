from odoo.tests.common import TransactionCase


class TestFirstStepsActions(TransactionCase):
    def test_import_product_actions_storable_only_with_stock(self):
        # The panel opens the storable action only when stock is installed.
        plain = self.env.ref("base_import_ux.action_first_steps_import_product")
        storable = self.env.ref("base_import_ux.action_first_steps_import_storable_product")
        self.assertNotIn("default_is_storable", plain.params["context"])
        self.assertNotIn("stock_product_template", plain.params["context"])
        self.assertTrue(storable.params["context"]["default_is_storable"])
        self.assertTrue(storable.params["context"]["stock_product_template"])
