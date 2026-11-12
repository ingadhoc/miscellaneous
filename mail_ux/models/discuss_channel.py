from odoo import models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def channel_fetched(self):
        """Same as upstream, but reads only the last message of each channel.

        Upstream resolves the whole ``message_ids`` one2many to keep its first id,
        which is slow on chats with many messages.
        """
        Message = self.env["mail.message"]
        for channel in self:
            if channel.channel_type not in {"chat", "whatsapp"}:
                continue
            # Same domain as message_ids, with the same access rules
            last_message_id = Message.search(
                [
                    ("model", "=", channel._name),
                    ("res_id", "=", channel.id),
                    ("message_type", "!=", "user_notification"),
                ],
                order="id desc",
                limit=1,
            ).id
            if not last_message_id:
                continue
            member = self.env["discuss.channel.member"].search(
                [("channel_id", "=", channel.id), ("partner_id", "=", self.env.user.partner_id.id)], limit=1
            )
            if not member:
                continue
            if member.fetched_message_id.id == last_message_id:
                continue
            # Avoid serialization error when multiple tabs are opened.
            query = """
                UPDATE discuss_channel_member
                SET fetched_message_id = %s
                WHERE id IN (
                    SELECT id FROM discuss_channel_member WHERE id = %s
                    FOR NO KEY UPDATE SKIP LOCKED
                )
            """
            self.env.cr.execute(query, (last_message_id, member.id))
            channel._bus_send(
                "discuss.channel.member/fetched",
                {
                    "channel_id": channel.id,
                    "id": member.id,
                    "last_message_id": last_message_id,
                    "partner_id": self.env.user.partner_id.id,
                },
            )
