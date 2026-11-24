##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.exceptions import AccessError
from odoo.tools import ormcache

from .field_edge_security import FIELD_EDGE_SECURITY


class Base(models.AbstractModel):
    """Keep the fields of `FIELD_EDGE_SECURITY` away from the two client read
    paths, without taking them away from the ORM.

    `groups=` on the field closes it for the server too, so the business logic
    that reads the field with the user breaks. This blanks it only where a
    client reads it: `_read_format` (read, search_read, web_read — the AI and
    API path) and `export_data`. The ORM keeps reading the field for itself,
    so the computes go on working.
    """

    _inherit = "base"

    @api.model
    @ormcache("self._name")
    def _edge_candidate_fields(self):
        """The declared fields this model really has. A field whose module is
        not installed is not in `_fields`, so its entry drops out here."""
        rules = FIELD_EDGE_SECURITY.get(self._name) or {}
        return tuple(name for name in rules if name in self._fields)

    @api.model
    def _edge_hidden_fields(self):
        """Of those, the ones this user may not read. Empty for the superuser."""
        names = self._edge_candidate_fields()
        if not names or self.env.su:
            return ()
        rules = FIELD_EDGE_SECURITY[self._name]
        return tuple(name for name in names if not self.env.user.has_groups(rules[name]))

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
        # An export spec can walk a relation ("product_variant_ids/standard_price"),
        # and the field at the end of the walk is as readable as a local one:
        # each hop is checked on the model it belongs to.
        for path in fields_to_export or ():
            model = self
            for name in str(path).split("/"):
                if name in model._edge_hidden_fields():
                    raise AccessError(
                        self.env._(
                            'You do not have enough rights to access the field "%(field)s" on %(document_model)s.',
                            field=name,
                            document_model=model._name,
                        )
                    )
                field = model._fields.get(name)
                if field is None or not field.comodel_name:
                    break
                model = self.env[field.comodel_name]
        return super().export_data(fields_to_export)
