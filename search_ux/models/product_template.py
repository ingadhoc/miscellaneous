##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
from odoo import api, fields, models
from odoo.fields import Domain

KEYWORDS_HELP = (
    "Aliases, synonyms, nicknames or trade names people use to look for this "
    "record. Internal use: it is neither printed nor published."
)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "search.ux.mixin"]

    _search_ux_default_paths = ("search_keywords",)

    # the label "Search Keywords" is derived from the field name
    search_keywords = fields.Char(index="trigram", help=KEYWORDS_HELP)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        results = super().name_search(name, domain, operator, limit)
        return self._search_ux_complete_name_search(results, name, domain, operator, limit)

    @api.model
    def _search_ux_related_domains(self, term, sources):
        """The related sources live on the variant: the template reuses them."""
        domains = super()._search_ux_related_domains(term, sources)
        variant_domains = self.env["product.product"]._search_ux_related_domains(term, sources)
        if variant_domains:
            domains.append(Domain("product_variant_ids", "any", Domain.OR(variant_domains)))
        return domains
