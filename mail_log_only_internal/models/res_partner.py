##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_mention_suggestions_domain(self, search):
        domain = super()._get_mention_suggestions_domain(search)
        internal_group = self.env.ref("base.group_user")
        internal_users = (
            self.env["res.users"]
            .search(
                [
                    ("groups_id", "in", internal_group.id),
                ]
            )
            .mapped("partner_id.id")
        )
        allow_ids_str = (
            self.env["ir.config_parameter"].sudo().get_param("mail_log_only_internal.allow_log_partner_ids", "[]")
        )

        try:
            allow_ids = safe_eval(allow_ids_str)
            if not isinstance(allow_ids, list):
                allow_ids = []
        except Exception:
            allow_ids = []

        allowed_partner_ids = internal_users + allow_ids
        return expression.AND([domain, [("id", "in", allowed_partner_ids)]])
