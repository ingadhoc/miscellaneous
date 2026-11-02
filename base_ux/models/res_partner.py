##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.modules.db import FunctionStatus

# Columns of res.partner._rec_names_search. The contact search ORs the five, so
# one of them without a trigram index sends the whole search to a Seq Scan.
SEARCH_COLUMNS = ("complete_name", "email", "ref", "vat", "company_registry")


def _trigram_index(column):
    """GIN trigram index on unaccent(column), next to whatever the registry builds."""

    def definition(registry):
        # Without an IMMUTABLE unaccent the index would be built without it and
        # no plan would use it: better no index than one nothing reads.
        if not registry.has_trigram or registry.has_unaccent != FunctionStatus.INDEXABLE:
            return ""
        return "USING gin (%s gin_trgm_ops)" % registry.unaccent('"%s"' % column)

    return models.Index(definition)


class ResPartner(models.Model):
    _inherit = "res.partner"

    _complete_name_trgm_index = _trigram_index("complete_name")
    _email_trgm_index = _trigram_index("email")
    _ref_trgm_index = _trigram_index("ref")
    _vat_trgm_index = _trigram_index("vat")
    _company_registry_trgm_index = _trigram_index("company_registry")

    active = fields.Boolean(tracking=True)

    @api.model
    def get_import_templates(self):
        if self.env.context.get("contact_import"):
            return [
                {
                    "label": _("Import Template for Contacts"),
                    "template": "/base_ux/static/xls/res_partner.xlsx",
                }
            ]
        return super().get_import_templates()
