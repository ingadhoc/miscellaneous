##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

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
