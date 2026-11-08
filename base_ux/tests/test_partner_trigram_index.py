##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.modules.db import FunctionStatus
from odoo.tests import TransactionCase

from ..models.res_partner import SEARCH_COLUMNS


class TestPartnerTrigramIndex(TransactionCase):
    def test_every_search_column_has_a_trigram_index(self):
        """The search ORs the five columns: one without its index is a Seq Scan."""
        registry = self.env.registry
        if not registry.has_trigram or registry.has_unaccent != FunctionStatus.INDEXABLE:
            self.skipTest("the database cannot hold a usable trigram index")
        self.env.cr.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'res_partner'")
        indexes = dict(self.env.cr.fetchall())
        for column in SEARCH_COLUMNS:
            definition = indexes.get("res_partner_%s_trgm_index" % column, "")
            self.assertIn("gin_trgm_ops", definition, "%s has no trigram index" % column)
            self.assertIn("unaccent", definition, "the index on %s would not be used" % column)
