##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
from odoo import api, fields, models
from odoo.fields import Domain

from .product_template import KEYWORDS_HELP
from .search_ux_mixin import LIKE_OPERATORS


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "search.ux.mixin"]

    _search_ux_default_paths = ("search_keywords",)

    # the label "Search Keywords" is derived from the field name
    search_keywords = fields.Char(index="trigram", help=KEYWORDS_HELP)

    @api.model
    def _search_display_name(self, operator, value):
        """The contact already searches declaratively: we add fields to that domain."""
        domain = super()._search_display_name(operator, value)
        if operator not in LIKE_OPERATORS or not isinstance(value, str):
            return domain
        extra = self._get_extra_search_domains(value)
        return Domain.OR([domain] + extra) if extra else domain
