##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
from odoo import api, fields, models, tools
from odoo.fields import Domain

DEFAULT_MIN_CHARS = 3
# the extended search only makes sense on partial match operators
LIKE_OPERATORS = ("ilike", "like")


class SearchUxMixin(models.AbstractModel):
    """Add configurable fields to the native search, without replacing it.

    It only runs when the native search did not fill the suggestion list, and
    always as a single query.
    """

    _name = "search.ux.mixin"
    _description = "Extended Search"

    # paths searched even without configuration (empty, they change nothing)
    _search_ux_default_paths = ()

    search_extended = fields.Char(
        compute="_compute_search_extended",
        search="_search_extended",
        help="Technical field: exposes the extended search to the search views, "
        "so the Search... box of the lists finds the same as the autocomplete.",
    )

    def _compute_search_extended(self):
        self.search_extended = False

    @api.model
    def _search_extended(self, operator, value):
        """Search seam for the list search views. Neutral when it does not apply."""
        if operator in Domain.NEGATIVE_OPERATORS:
            return Domain.TRUE
        if operator not in LIKE_OPERATORS or not isinstance(value, str):
            return Domain.FALSE
        extra = self._get_extra_search_domains(value)
        return Domain.OR(extra) if extra else Domain.FALSE

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        """Extend the free text search of the search views with the seam.

        It is done here and not in XML because other modules rewrite the
        filter_domain of that field (partner_internal_code, for one) and the
        last one to write it would win.
        """
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "search" or not self._search_ux_settings()[0]:
            return arch, view
        node = arch.find(".//field")
        if node is None or not node.get("name"):
            return arch, view
        native = (node.get("filter_domain") or "").strip()
        if not native:
            native = "[('%s', 'ilike', self)]" % node.get("name")
        if "search_extended" in native or not native.startswith("[") or not native.endswith("]"):
            return arch, view
        node.set(
            "filter_domain",
            "['|', %s, ('search_extended', 'ilike', self)]" % native[1:-1],
        )
        return arch, view

    @api.model
    @tools.ormcache("self._name")
    def _search_ux_settings(self):
        """(paths, min_chars, related sources) of the model, cached."""
        config = (
            self.env["search.ux.config"]
            .sudo()
            .with_context(active_test=False)
            .search([("model", "=", self._name)], limit=1)
        )
        if config and not config.active:
            return ((), DEFAULT_MIN_CHARS, ())
        paths = tuple(self._search_ux_default_paths) + tuple(config.field_ids.mapped("path"))
        return (
            paths,
            config.min_chars if config else DEFAULT_MIN_CHARS,
            config._enabled_sources() if config else (),
        )

    @api.model
    def _get_extra_search_domains(self, term):
        """Extra domains to search `term`. Extension point: inherit with super()."""
        paths, min_chars, sources = self._search_ux_settings()
        if not term or not isinstance(term, str) or len(term) < min_chars:
            return []
        domains = []
        if paths:
            # every word, in any order and on any field
            domains.append(
                Domain.AND([Domain.OR([Domain(path, "ilike", word) for path in paths]) for word in term.split()])
            )
        return domains + self._search_ux_related_domains(term, sources)

    @api.model
    def _search_ux_related_domains(self, term, sources):
        """Domains of the related sources enabled on the configuration."""
        return []

    @api.model
    def _search_ux_can_read(self, model_name):
        """A source the user cannot read is skipped, never raised."""
        return model_name in self.env and self.env[model_name].has_access("read")

    @api.model
    def _search_ux_extend(self, ids, term, domain, limit):
        """Complete `ids` with the extra domains, in a single query."""
        if limit and len(ids) >= limit:
            return ids
        extra = self._get_extra_search_domains(term)
        if not extra:
            return ids
        full_domain = Domain.AND(
            [
                Domain(domain or Domain.TRUE),
                Domain.OR(extra),
                Domain("id", "not in", list(ids)),
            ]
        )
        return list(ids) + list(self._search(full_domain, limit=limit and limit - len(ids)))

    @api.model
    def _search_ux_complete_name_search(self, results, term, domain, operator, limit):
        """Add to the native name_search result whatever the extra domains bring."""
        if not term or operator not in LIKE_OPERATORS:
            return results
        ids = self._search_ux_extend([res[0] for res in results], term, domain, limit)
        extra_ids = ids[len(results) :]
        if not extra_ids:
            return results
        return results + [(record.id, record.display_name) for record in self.browse(extra_ids)]
