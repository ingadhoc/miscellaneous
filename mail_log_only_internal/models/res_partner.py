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
        all_users = self.env["res.users"].search([("active", "=", True)])
        internal_users = all_users.filtered(lambda u: u.has_group("base.group_user") and u.partner_id).mapped(
            "partner_id.id"
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
        if allow_ids:
            existing_ids = self.env["res.partner"].search([("id", "in", allow_ids)]).ids
            allow_ids = existing_ids
        return internal_users + allow_ids

    @api.model
    def _get_mention_suggestions_domain(self, search):
        domain = super()._get_mention_suggestions_domain(search)
        allowed_partner_ids = self._get_allowed_partner_ids()
        return Domain.AND([domain, [("id", "in", allowed_partner_ids)]])

    @api.model
    def _search_mention_suggestions(self, domain, limit, extra_domain=None):
        allowed_partner_ids = self._get_allowed_partner_ids()
        domain = Domain.AND([domain, [("id", "in", allowed_partner_ids)]])
        return super()._search_mention_suggestions(domain, limit, extra_domain)

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        result = super().get_mention_suggestions(search, limit)
        allowed_partner_ids = self._get_allowed_partner_ids()
        if isinstance(result, dict) and "res.partner" in result:
            filtered_partners = [
                partner for partner in result["res.partner"] if partner.get("id") in allowed_partner_ids
            ]
            result["res.partner"] = filtered_partners
            if "hr.employee" in result:
                allowed_employees = (
                    self.env["res.partner"].browse(allowed_partner_ids).mapped("user_ids.employee_ids.id")
                )
                result["hr.employee"] = [emp for emp in result["hr.employee"] if emp.get("id") in allowed_employees]
            if "res.users" in result:
                allowed_users = self.env["res.partner"].browse(allowed_partner_ids).mapped("user_ids.id")
                result["res.users"] = [user for user in result["res.users"] if user.get("id") in allowed_users]
        return result

    @api.model
    def _search_for_channel_invite(self, store, search_term, channel_id=None, limit=30):
        result = super()._search_for_channel_invite(store, search_term, channel_id, limit)
        allowed_partner_ids = self._get_allowed_partner_ids()
        result["partner_ids"] = [pid for pid in result.get("partner_ids", []) if pid in allowed_partner_ids]
        result["count"] = len(result["partner_ids"])
        return result
