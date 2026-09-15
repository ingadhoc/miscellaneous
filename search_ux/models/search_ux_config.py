##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .search_ux_mixin import DEFAULT_MIN_CHARS

DEFAULT_MAX_FIELDS = 5
MAX_FIELDS_PARAM = "search_ux.max_fields"
SEARCHABLE_TYPES = ("char", "text")
RELATED_SOURCES = ("lot", "supplier_code", "packaging_barcode")


def _invalidate(env):
    """The settings live in an ormcache and the seam is injected in the views."""
    env.registry.clear_cache()
    env.registry.clear_cache("templates")


class SearchUxConfig(models.Model):
    _name = "search.ux.config"
    _description = "Extended Search Configuration"
    _rec_name = "model_id"

    model_id = fields.Many2one(
        "ir.model",
        "Model",
        required=True,
        ondelete="cascade",
        domain="[('model', 'in', available_models)]",
    )
    model = fields.Char("Technical Name", related="model_id.model", store=True, index=True)
    available_models = fields.Json(compute="_compute_available_models")
    field_ids = fields.One2many(
        "search.ux.field",
        "config_id",
        "Fields to Include",
        help="Text fields added to the search when the native one does not " "fill the suggestion list.",
    )
    min_chars = fields.Integer(
        "Minimum Characters",
        default=DEFAULT_MIN_CHARS,
        required=True,
        help="Number of characters from which the extended search is triggered.",
    )
    search_lot = fields.Boolean("Search by Lot / Serial")
    search_supplier_code = fields.Boolean("Search by Vendor Code")
    search_packaging_barcode = fields.Boolean("Search by Packaging Barcode")
    active = fields.Boolean(default=True)

    _model_uniq = models.Constraint(
        "unique(model_id)",
        "There is already an extended search configuration for this model.",
    )

    def _compute_available_models(self):
        models_ = sorted(
            name
            for name, model in self.env.registry.items()
            if hasattr(model, "_search_ux_default_paths") and not model._abstract
        )
        self.available_models = models_

    def _enabled_sources(self):
        self.ensure_one()
        return tuple(source for source in RELATED_SOURCES if self["search_%s" % source])

    def _max_fields(self):
        return int(self.env["ir.config_parameter"].sudo().get_param(MAX_FIELDS_PARAM, DEFAULT_MAX_FIELDS))

    @api.constrains("model_id")
    def _check_model(self):
        for rec in self:
            model = self.env.get(rec.model_id.model)
            if model is None or not hasattr(model, "_search_ux_default_paths"):
                raise ValidationError(
                    self.env._(
                        'Model "%s" does not implement the extended search. It can '
                        "only be configured on the models that inherit it explicitly "
                        "(product and contact).",
                        rec.model_id.model,
                    )
                )

    @api.constrains("field_ids")
    def _check_max_fields(self):
        max_fields = self._max_fields()
        for rec in self:
            if len(rec.field_ids) > max_fields:
                raise ValidationError(
                    self.env._(
                        "You configured %(count)s fields on %(model)s and the maximum "
                        "is %(max)s. More fields make the search slower: if you need "
                        'several criteria, load them in "Search Keywords".',
                        count=len(rec.field_ids),
                        model=rec.model,
                        max=max_fields,
                    )
                )

    @api.constrains("min_chars")
    def _check_min_chars(self):
        for rec in self.filtered(lambda x: x.min_chars < 1):
            raise ValidationError(self.env._("The minimum number of characters must be at least 1."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _invalidate(self.env)
        return records

    def write(self, vals):
        res = super().write(vals)
        _invalidate(self.env)
        return res

    def unlink(self):
        res = super().unlink()
        _invalidate(self.env)
        return res


class SearchUxField(models.Model):
    _name = "search.ux.field"
    _description = "Extended Search Field"
    _rec_name = "path"

    config_id = fields.Many2one("search.ux.config", "Configuration", required=True, ondelete="cascade")
    model = fields.Char(related="config_id.model", string="Model Name")
    path = fields.Char(
        "Field",
        required=True,
        help="Technical name of the field, or forward path " "(product_tmpl_id.my_field).",
    )

    @api.constrains("path", "config_id")
    def _check_path(self):
        for rec in self:
            rec._validate_path()
            # the limit per model is also checked when adding a single line
            rec.config_id._check_max_fields()

    def _validate_path(self):
        """Reject what cannot be searched in SQL or degrades the search."""
        self.ensure_one()
        model = self.env.get(self.config_id.model_id.model)
        if model is None:
            return
        parts = (self.path or "").split(".")
        for index, name in enumerate(parts):
            field = model._fields.get(name)
            if field is None:
                raise ValidationError(
                    self.env._(
                        'Field "%(path)s" does not exist on %(model)s.',
                        path=self.path,
                        model=model._name,
                    )
                )
            if index < len(parts) - 1:
                if not field.comodel_name:
                    raise ValidationError(
                        self.env._(
                            '"%s" is not a relational field, the path cannot be ' "followed.",
                            name,
                        )
                    )
                model = self.env[field.comodel_name]
            else:
                self._check_searchable(field)

    def _check_searchable(self, field):
        if field.type == "html":
            raise ValidationError(
                self.env._(
                    '"%s" is an HTML field. Searching inside HTML is the main cause '
                    "of slow searches: use a text field, or load the aliases in "
                    '"Search Keywords".',
                    field.string,
                )
            )
        if field.type in ("binary", "image"):
            raise ValidationError(self.env._('"%s" is an attachment, it cannot be searched.', field.string))
        if not field.store:
            raise ValidationError(
                self.env._(
                    '"%s" is not stored in the database, it cannot be searched in SQL.',
                    field.string,
                )
            )
        if field.type not in SEARCHABLE_TYPES:
            raise ValidationError(
                self.env._(
                    '"%(name)s" is a %(type)s field. Only text fields can be searched.',
                    name=field.string,
                    type=field.type,
                )
            )
        if field.groups:
            raise ValidationError(
                self.env._(
                    '"%s" is restricted by groups: users without access would get an ' "error when searching.",
                    field.string,
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _invalidate(self.env)
        return records

    def write(self, vals):
        res = super().write(vals)
        _invalidate(self.env)
        return res

    def unlink(self):
        res = super().unlink()
        _invalidate(self.env)
        return res
