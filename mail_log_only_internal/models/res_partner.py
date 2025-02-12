##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.osv import expression


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
        return expression.AND([domain, [("id", "in", internal_users)]])
