##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "search.ux.mixin"]

    # the keywords live on the template
    _search_ux_default_paths = ("product_tmpl_id.search_keywords",)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        results = super().name_search(name, domain, operator, limit)
        return self._search_ux_complete_name_search(results, name, domain, operator, limit)

    @api.model
    def _search_ux_related_domains(self, term, sources):
        domains = super()._search_ux_related_domains(term, sources)
        if "supplier_code" in sources and self._search_ux_can_read("product.supplierinfo"):
            sellers = self.env["product.supplierinfo"]._search([("product_code", "ilike", term)])
            domains.append(
                Domain("id", "in", sellers.subselect("product_id"))
                | Domain("product_tmpl_id", "in", sellers.subselect("product_tmpl_id"))
            )
        if "packaging_barcode" in sources and self._search_ux_can_read("product.uom"):
            packagings = self.env["product.uom"]._search([("barcode", "ilike", term)])
            domains.append(Domain("id", "in", packagings.subselect("product_id")))
        if "lot" in sources and self._search_ux_can_read("stock.lot"):
            lots = self.env["stock.lot"]._search([("name", "ilike", term)])
            domains.append(Domain("id", "in", lots.subselect("product_id")))
        return domains
