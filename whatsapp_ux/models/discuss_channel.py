##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.whatsapp.models.discuss_channel import is_whatsapp_channel


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _whatsapp_get_owner_partner(self):
        """Same owner rule as the native leave guard: the first internal member."""
        self.ensure_one()
        return next(
            (member.partner_id for member in self.channel_member_ids if not member.partner_id.partner_share),
            self.env["res.partner"],
        )

    def _to_store_defaults(self, target):
        # The owner id (not a "self is owner" flag) because the store is also broadcast to other members.
        return super()._to_store_defaults(target) + [
            Store.Attr(
                "whatsapp_owner_partner_id",
                lambda channel: channel._whatsapp_get_owner_partner().id,
                predicate=is_whatsapp_channel,
            ),
        ]
