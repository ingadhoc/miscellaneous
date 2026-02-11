##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.fields import Domain
from odoo.tools.safe_eval import safe_eval


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_allowed_partner_ids(self):
        internal_group = self.env.ref("base.group_user")
        internal_users = internal_group.all_user_ids.mapped("partner_id.id")

        allow_ids_str = (
            self.env["ir.config_parameter"].sudo().get_param("mail_log_only_internal.allow_log_partner_ids", "[]")
        )
        try:
            allow_ids = safe_eval(allow_ids_str)
            if not isinstance(allow_ids, list):
                allow_ids = []
        except Exception:
            allow_ids = []
        if allow_ids:
            existing_ids = self.env["res.partner"].search([("id", "in", allow_ids)]).ids
            allow_ids = existing_ids
        return internal_users + allow_ids

    @api.model
    def _get_mention_suggestions_domain(self, search):
        domain = super()._get_mention_suggestions_domain(search)
        allowed_partner_ids = self._get_allowed_partner_ids()
        return Domain.AND([domain, [("id", "in", allowed_partner_ids)]])
