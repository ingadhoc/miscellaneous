##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.exceptions import AccessError
from odoo.tools import ormcache


class Base(models.AbstractModel):
    """Keep a field out of every path a client can read it from, without taking
    it away from the ORM.

    `groups=` closes the field for the server too: `Field.__get__` checks it
    since 19.0, so the business logic that reads the field with the user stops
    working. This closes only the edge: what a client can discover, read,
    filter, group, order and export. The ORM keeps reading the field for
    itself, so the computes and the valuation go on working.

    Declared per field, next to the field:

        standard_price = fields.Float(
            edge_groups="!price_security.group_only_view_sale_price")

    The value is a `has_groups` spec, so it reads like `groups=`: the groups
    that MAY read it, with `!` for the ones that may not.
    """

    _inherit = "base"

    def _valid_field_parameter(self, field, name):
        return name == "edge_groups" or super()._valid_field_parameter(field, name)

    @api.model
    @ormcache("self._name")
    def _edge_candidate_fields(self):
        """Fields of this model that declare `edge_groups`. Static per model."""
        return tuple(name for name, field in self._fields.items() if getattr(field, "edge_groups", None))

    @api.model
    def _edge_hidden_fields(self):
        """Of those, the ones this user may not read. Empty for the superuser."""
        names = self._edge_candidate_fields()
        if not names or self.env.su:
            return ()
        return tuple(name for name in names if not self.env.user.has_groups(self._fields[name].edge_groups))

    # -- the six read paths ---------------------------------------------------

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        for name in self._edge_hidden_fields():
            res.pop(name, None)
        return res

    def _read_format(self, fnames, load="_classic_read"):
        res = super()._read_format(fnames, load)
        hidden = self._edge_hidden_fields()
        if hidden:
            for values in res:
                for name in hidden:
                    if name in values:
                        values[name] = False
        return res

    def export_data(self, fields_to_export):
        self._edge_check_specs(fields_to_export)
        return super().export_data(fields_to_export)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        if self._edge_candidate_fields():
            self._edge_check_domain(domain)
            self._edge_check_order(order)
        return super()._search(domain, offset, limit, order, **kwargs)

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        if self._edge_candidate_fields():
            self._edge_check_domain(domain)
            self._edge_check_domain(having)
            self._edge_check_specs(groupby)
            self._edge_check_specs(aggregates)
            self._edge_check_order(order)
        return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

    # -- the arch -------------------------------------------------------------
    #
    # A field the user cannot read has to leave the arch: the web client
    # resolves every <field> node against what the view returns and raises
    # "field is undefined" when one is missing. Marking it invisible is not
    # enough, the node itself has to go.

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type="form", **options):
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + self._edge_hidden_fields()

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        self._edge_drop_nodes(arch)
        return arch, view

    @api.model
    def _edge_drop_nodes(self, arch):
        """Drop the hidden fields of every model in the arch, not only of self:
        an embedded x2many list carries the comodel fields inline. Living on
        `base` is what makes this work for a comodel nobody declared."""
        for node in list(arch.iter("field")):
            name = node.get("name")
            if name not in self._edge_node_model(node)._edge_hidden_fields():
                continue
            for label in arch.xpath("//label[@for='%s']" % name):
                label.getparent().remove(label)
            node.getparent().remove(node)

    @api.model
    def _edge_node_model(self, node):
        """The model a <field> node belongs to, walking up the x2many chain."""
        chain = []
        parent = node.getparent()
        while parent is not None:
            if parent.tag == "field":
                chain.append(parent.get("name"))
            parent = parent.getparent()
        model = self
        for name in reversed(chain):
            field = model._fields.get(name)
            if field is None or not field.comodel_name:
                return self.env["base"]
            model = self.env[field.comodel_name]
        return model

    # -- helpers --------------------------------------------------------------

    @api.model
    def _edge_check_specs(self, specs):
        """`specs` are field expressions: "margin", "margin:sum", "date:month"."""
        for spec in specs or ():
            self._edge_check_field(str(spec).split(":")[0].split(".")[0])

    @api.model
    def _edge_check_domain(self, domain):
        for condition in domain or ():
            if isinstance(condition, (tuple, list)) and len(condition) == 3 and isinstance(condition[0], str):
                self._edge_check_field(condition[0].split(":")[0].split(".")[0])

    @api.model
    def _edge_check_order(self, order):
        for term in (order or "").split(","):
            if term.strip():
                self._edge_check_field(term.split()[0].split(":")[0].split(".")[0])

    @api.model
    def _edge_check_field(self, name):
        if name in self._edge_hidden_fields():
            raise AccessError(
                self.env._(
                    'You do not have enough rights to access the field "%(field)s" on %(document_model)s.',
                    field=name,
                    document_model=self._name,
                )
            )
