##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

import psycopg2
from odoo import fields, models
from odoo.modules.db import FunctionStatus
from odoo.tools import create_index

_logger = logging.getLogger(__name__)

# Fields searched by name_search: _rec_names_search plus name.
TRIGRAM_INDEXED_FIELDS = ("name", "complete_name", "email", "ref", "vat")


class ResPartner(models.Model):
    _inherit = "res.partner"

    active = fields.Boolean(tracking=True)

    def init(self):
        super().init()
        self._create_search_trigram_indexes()

    def _create_search_trigram_indexes(self):
        """Add gin trigram indexes for ILIKE on the partner search fields.

        They go next to the btree indexes from core, with their own names: an
        index="trigram" on the field would make the registry drop the btree and
        rebuild it as gin without CONCURRENTLY, and the btree is what serves "=".
        """
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
            indexname = f"res_partner__{field_name}_trgm_index"
            column = registry.unaccent(f'"{field_name}"')
            # Same as the registry: a failed index must not abort the module update.
            try:
                with self.env.cr.savepoint(flush=False):
                    create_index(
                        self.env.cr,
                        indexname=indexname,
                        tablename="res_partner",
                        expressions=[f"{column} gin_trgm_ops"],
                        method="gin",
                    )
            except psycopg2.OperationalError:
                _logger.error("Unable to add index %s on res_partner", indexname)
