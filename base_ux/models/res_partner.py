##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
<<<<<<< 50e95b33c6d5bd1994e00dae22440b71eed52adb
from odoo import _, api, fields, models
||||||| 96234c8c8dac09b4682ba4489e4e035cc529d8b6
from odoo import fields, models
=======
import logging

from odoo import fields, models
from odoo.modules.db import FunctionStatus
from odoo.tools import create_index

_logger = logging.getLogger(__name__)

# Fields searched by name_search: _rec_names_search plus name.
TRIGRAM_INDEXED_FIELDS = ("name", "complete_name", "email", "ref", "vat")
# Same convention as saas_client feature flags; read directly to avoid the dependency.
TRIGRAM_FLAG_PARAM = "saas_feature.partner_search_trigram_index"
>>>>>>> b23f001a580bbc9168e2801bc8619e6922d5780e


class ResPartner(models.Model):
    _inherit = "res.partner"

    active = fields.Boolean(tracking=True)
<<<<<<< 50e95b33c6d5bd1994e00dae22440b71eed52adb

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
||||||| 96234c8c8dac09b4682ba4489e4e035cc529d8b6
=======

    def init(self):
        super().init()
        self._create_search_trigram_indexes()

    def _create_search_trigram_indexes(self):
        """Add gin trigram indexes for ILIKE on the partner search fields.

        They go next to the btree indexes from core, with their own names: an
        index="trigram" on the field would make the registry drop the btree and
        rebuild it as gin without CONCURRENTLY, and the btree is what serves "=".
        Only runs when the feature flag is on, so the rollout goes base by base.
        """
        flag = self.env["ir.config_parameter"].sudo().get_param(TRIGRAM_FLAG_PARAM, "")
        if flag.strip().lower() not in ("1", "true", "yes"):
            return
        registry = self.env.registry
        # Logged at info: a WARNING during install turns the runbot build red.
        if not registry.has_trigram:
            _logger.info("pg_trgm is missing: res.partner search trigram indexes are not created.")
            return
        # Without an IMMUTABLE unaccent the index would not match the ORM query.
        if registry.has_unaccent != FunctionStatus.INDEXABLE:
            _logger.info("unaccent is not indexable: res.partner search trigram indexes are not created.")
            return
        for field_name in TRIGRAM_INDEXED_FIELDS:
            column = registry.unaccent(f'"{field_name}"')
            create_index(
                self.env.cr,
                indexname=f"res_partner__{field_name}_trgm_index",
                tablename="res_partner",
                expressions=[f"{column} gin_trgm_ops"],
                method="gin",
            )
>>>>>>> b23f001a580bbc9168e2801bc8619e6922d5780e
