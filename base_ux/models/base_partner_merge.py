##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from collections import defaultdict

from odoo import Command, models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _deduplicate_mail_followers(self, src_partners, dst_partner):
        followers_by_document = defaultdict(lambda: self.env["mail.followers"])
        partners_to_merge = src_partners | dst_partner
        followers = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("partner_id", "in", partners_to_merge.ids),
                ]
            )
        )

        for follower in followers:
            res_id = follower.res_id.id if hasattr(follower.res_id, "id") else follower.res_id
            key = (follower.res_model, res_id or 0)
            followers_by_document[key] = followers_by_document[key] | follower

        for grouped_followers in followers_by_document.values():
            if len(grouped_followers) < 2:
                continue

            keeper = grouped_followers.filtered(lambda follower: follower.partner_id == dst_partner)[:1]
            keeper = keeper or grouped_followers[:1]
            duplicates = grouped_followers - keeper
            subtype_ids = grouped_followers.mapped("subtype_ids")

            if set(subtype_ids.ids) != set(keeper.subtype_ids.ids):
                keeper.write({"subtype_ids": [Command.set(subtype_ids.ids)]})

            duplicates.unlink()

    def _update_foreign_keys(self, src_partners, dst_partner):
        self._deduplicate_mail_followers(src_partners, dst_partner)
        return super()._update_foreign_keys(src_partners, dst_partner)
