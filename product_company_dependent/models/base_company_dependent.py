from odoo import models


class BaseCompanyDependent(models.AbstractModel):
    _inherit = "base.company.dependent"

    def _resolve_orm_target(self, res_model, res_id, field_name):
        """Send a single-variant template field to its company dependent
        variant field, so the dialog reads and writes the real JSONB value.

        With several variants the target stays on the template: reading gives
        the computed value and writing goes to every variant through the
        inverse, as in standard Odoo.
        """
        target = super()._resolve_orm_target(res_model, res_id, field_name)
        if res_model != "product.template" or target != (res_model, field_name, res_id):
            return target
        variants = self.env["product.template"].browse(res_id).product_variant_ids
        variant_field = self.env["product.product"]._fields.get(field_name)
        if len(variants) == 1 and variant_field and variant_field.company_dependent:
            return "product.product", field_name, variants.id
        return target
