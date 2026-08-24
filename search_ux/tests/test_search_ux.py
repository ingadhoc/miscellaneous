##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSearchUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Product = cls.env["product.product"]
        cls.Config = cls.env["search.ux.config"]
        cls.product_model = cls.env.ref("product.model_product_product")
        cls.partner_model = cls.env.ref("base.model_res_partner")
        cls.template_model = cls.env.ref("product.model_product_template")
        cls.product = cls.Product.create(
            {
                "name": "Ergonomic Chair",
                "default_code": "CHA-01",
                "search_keywords": "clappen alfa",
                "description_sale": "beta armrest",
            }
        )
        cls.other = cls.Product.create({"name": "Fixed Chair", "default_code": "CHA-02"})
        cls.partner = cls.env["res.partner"].create({"name": "Southern Real Estate SA", "search_keywords": "remax"})

    def _config(self, model_record, **vals):
        return self.Config.create(dict(vals, model_id=model_record.id))

    def _name_search_ids(self, model, term, **kwargs):
        return [res[0] for res in self.env[model].name_search(term, **kwargs)]

    def test_keywords_product(self):
        """The product keyword finds the variant without configuring anything."""
        self.assertIn(self.product.id, self._name_search_ids("product.product", "clappen"))

    def test_keywords_template(self):
        """The template searches by keyword too (many2one to product.template)."""
        found = self._name_search_ids("product.template", "clappen")
        self.assertIn(self.product.product_tmpl_id.id, found)

    def test_keywords_partner(self):
        """On contacts it is enough to add the field to the declarative domain."""
        self.assertIn(self.partner.id, self._name_search_ids("res.partner", "remax"))

    def test_native_result_without_configuration(self):
        """AC5: without configuration nor keywords, the result is Odoo's."""
        found = set(self._name_search_ids("product.product", "Fixed Chair"))
        native = self.Product.search([("name", "ilike", "Fixed Chair")])
        self.assertEqual(found, set(native.ids))

    def test_skipped_when_native_fills_the_list(self):
        """If the native search filled the limit, the extended one does not run."""
        with patch.object(type(self.Product), "_get_extra_search_domains", autospec=True) as spy:
            self.Product.name_search("Chair", limit=1)
            spy.assert_not_called()

    def test_multi_word_single_query(self):
        """Every word, in any order and on any configured field, in one query."""
        config = self._config(self.product_model)
        self.env["search.ux.field"].create({"config_id": config.id, "path": "product_tmpl_id.description_sale"})
        product_class = type(self.Product)
        original_search = product_class._search
        calls = []

        def counting_search(self, *args, **kwargs):
            calls.append(args)
            return original_search(self, *args, **kwargs)

        with patch.object(product_class, "_search", counting_search):
            found = self.Product._search_ux_extend([], "beta clappen", None, 10)
        self.assertEqual(len(calls), 1, "the extended search must be a single query")
        self.assertIn(self.product.id, found)
        self.assertNotIn(self.product.id, self._name_search_ids("product.product", "beta missing"))

    def test_minimum_characters(self):
        """Below the configured minimum the extended search is not triggered."""
        self._config(self.product_model, min_chars=6)
        self.assertNotIn(self.product.id, self._name_search_ids("product.product", "clapp"))
        self.assertIn(self.product.id, self._name_search_ids("product.product", "clappen"))

    def test_turned_off(self):
        """Archiving the configuration leaves the model with the bare native search."""
        config = self._config(self.product_model)
        config.active = False
        self.assertNotIn(self.product.id, self._name_search_ids("product.product", "clappen"))

    def test_honours_the_received_domain(self):
        """The domain of the line wins, even if the keyword matches."""
        self.product.sale_ok = False
        found = self._name_search_ids("product.product", "clappen", domain=[("sale_ok", "=", True)])
        self.assertNotIn(self.product.id, found)

    def test_extension_point(self):
        """A customer module adds its source inheriting _get_extra_search_domains."""
        product_class = type(self.Product)
        original = product_class._get_extra_search_domains

        def with_extra_source(self, term):
            return original(self, term) + [Domain("default_code", "=", "CHA-02")]

        with patch.object(product_class, "_get_extra_search_domains", with_extra_source):
            found = self._name_search_ids("product.product", "missing")
        self.assertEqual(found, self.other.ids)

    def test_exact_operators_are_not_extended(self):
        """An exact search must not match through the keywords."""
        self.assertFalse(self._name_search_ids("product.product", "clappen", operator="="))
        self.assertFalse(self._name_search_ids("product.product", "clappen", operator="=ilike"))
        self.assertIn(self.product.id, self._name_search_ids("product.product", "clappen"))
        exact_domain = self.env["res.partner"]._search_display_name("=", "remax")
        self.assertNotIn("search_keywords", str(exact_domain))

    def test_source_without_access_is_skipped(self):
        """A related source the user cannot read is skipped, it does not raise."""
        if "stock.lot" not in self.env:
            self.skipTest("stock is not installed")
        self._config(self.product_model, search_lot=True)
        user = self.env["res.users"].create(
            {
                "name": "No Inventory",
                "login": "search_ux_no_inventory",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        found = self.env["product.product"].with_user(user).name_search("clappen")
        self.assertIn(self.product.id, [res[0] for res in found])

    def test_list_search_finds_the_same_as_the_autocomplete(self):
        """AC4: both surfaces return the same records for the same term."""
        term = "clappen"
        autocomplete = set(self._name_search_ids("product.product", term))
        list_box = set(
            self.Product.search(
                [
                    "|",
                    "|",
                    "|",
                    ("default_code", "ilike", term),
                    ("name", "ilike", term),
                    ("barcode", "ilike", term),
                    ("search_extended", "ilike", term),
                ]
            ).ids
        )
        self.assertEqual(autocomplete, list_box)
        self.assertIn(self.product.id, list_box)

    def test_list_search_on_partners(self):
        """AC4 on contacts: their search box already goes through display_name."""
        found = self.env["res.partner"].search([("display_name", "ilike", "remax")])
        self.assertIn(self.partner.id, found.ids)

    def test_template_reuses_the_variant_related_sources(self):
        """AC4: a lot found on the variant also finds the template in its list."""
        if "stock.lot" not in self.env:
            self.skipTest("stock is not installed")
        self._config(self.template_model, search_lot=True)
        self.env["stock.lot"].create({"name": "SERIAL-XYZ", "product_id": self.product.id})
        found = self._name_search_ids("product.template", "SERIAL-XYZ")
        self.assertIn(self.product.product_tmpl_id.id, found)

    def test_search_views_use_the_extended_seam(self):
        """The free text search of the list views goes through the extended search."""
        views = [
            ("product.template", "product.product_template_search_view"),
            ("product.product", "product.product_search_form_view"),
            ("product.product", "product.product_view_search_catalog"),
            ("res.partner", "base.view_res_partner_filter"),
        ]
        for model, xmlid in views:
            with self.subTest(view=xmlid):
                arch = self.env[model].get_view(self.env.ref(xmlid).id, "search")["arch"]
                self.assertIn("search_extended", arch)

    def test_seam_composes_with_other_modules(self):
        """The seam is added to whatever filter_domain the view already carried."""
        view = self.env.ref("base.view_res_partner_filter")
        view.write(
            {
                "arch_db": view.arch_db.replace(
                    "[('display_name', 'ilike', self)]",
                    "[('complete_name', 'ilike', self)]",
                )
            }
        )
        arch = self.env["res.partner"].get_view(view.id, "search")["arch"]
        self.assertIn("complete_name", arch)
        self.assertIn("search_extended", arch)

    def test_no_seam_when_turned_off(self):
        """With the configuration archived the search views are left untouched."""
        config = self._config(self.partner_model)
        config.active = False
        arch = self.env["res.partner"].get_view(self.env.ref("base.view_res_partner_filter").id, "search")["arch"]
        self.assertNotIn("search_extended", arch)

    def test_rejects_fields_that_cannot_be_sustained(self):
        """HTML, non stored, missing and non textual fields are rejected on save."""
        cases = [
            (self.template_model, "description"),
            (self.partner_model, "contact_address"),
            (self.partner_model, "field_that_does_not_exist"),
            (self.partner_model, "active"),
            (self.partner_model, "parent_id.missing"),
        ]
        for model_record, path in cases:
            with self.subTest(path=path), self.assertRaises(ValidationError):
                with self.env.cr.savepoint():
                    config = self.Config.search([("model_id", "=", model_record.id)]) or self._config(model_record)
                    self.env["search.ux.field"].create({"config_id": config.id, "path": path})

    def test_rejects_more_than_five_fields(self):
        """The field limit per model is part of the contract, not a recommendation."""
        config = self._config(self.partner_model)
        paths = ["ref", "vat", "website", "phone", "email", "city"]
        with self.assertRaises(ValidationError):
            self.env["search.ux.field"].create([{"config_id": config.id, "path": path} for path in paths])

    def test_only_on_models_implementing_it(self):
        """The extended search cannot be turned on for any model of the registry."""
        with self.assertRaises(ValidationError):
            self._config(self.env.ref("base.model_res_users"))
