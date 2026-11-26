from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestProductCompanyDependent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.helper = cls.env["base.company.dependent"]
        cls.template = cls.env["product.template"].create({"name": "CD Test Product"})

    def test_detect_strategy_computed_company_context(self):
        """A computed field with @api.depends_context('company') uses ORM mode."""
        self.assertEqual(self.helper._detect_field_strategy("product.template", "standard_price"), "orm")

    def test_resolve_single_variant_to_variant(self):
        target = self.helper._resolve_orm_target("product.template", self.template.id, "standard_price")
        self.assertEqual(target, ("product.product", "standard_price", self.template.product_variant_id.id))

    def test_resolve_other_model_untouched(self):
        partner = self.env["res.partner"].create({"name": "CD Test Partner"})
        target = self.helper._resolve_orm_target("res.partner", partner.id, "barcode")
        self.assertEqual(target, ("res.partner", "barcode", partner.id))

    def test_refuse_template_with_several_variants(self):
        """The template inverse only writes with a single variant, so the
        dialog must not report a save that never happens."""
        attribute = self.env["product.attribute"].create(
            {"name": "CD Size", "value_ids": [(0, 0, {"name": "S"}), (0, 0, {"name": "M"})]}
        )
        template = self.env["product.template"].create(
            {
                "name": "CD Multi Variant",
                "attribute_line_ids": [
                    (0, 0, {"attribute_id": attribute.id, "value_ids": [(6, 0, attribute.value_ids.ids)]})
                ],
            }
        )
        self.assertEqual(len(template.product_variant_ids), 2)
        with self.assertRaises(UserError):
            self.helper.get_company_dependent_values("product.template", template.id, "standard_price", mode="orm")
        with self.assertRaises(UserError):
            self.helper.set_company_dependent_values(
                "product.template", template.id, "standard_price", {str(self.env.company.id): 10.0}, mode="orm"
            )

    def test_meta_reports_template_standard_price(self):
        """A single-variant template reports standard_price as specific once
        the variant has a per-company value."""
        self.template.product_variant_id.with_company(self.env.company).standard_price = 42.0
        self.env.flush_all()
        meta = self.helper.get_company_dependent_meta("product.template", self.template.id)
        self.assertTrue(meta.get("standard_price"))
