import inspect
from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestChannelFetched(MailCommon):
    def _search_spy(self):
        MailMessage = self.env.registry["mail.message"]
        return patch.object(MailMessage, "_search", autospec=True, side_effect=MailMessage._search)

    def _search_limits(self, spy):
        signature = inspect.signature(self.env.registry["mail.message"]._search)
        return [signature.bind(*call.args, **call.kwargs).arguments.get("limit") for call in spy.call_args_list]

    def test_chat_fetched_reads_only_last_message(self):
        chat = (
            self.env["discuss.channel"].with_user(self.user_employee).channel_get(partners_to=[self.partner_admin.id])
        )
        messages = self.env["mail.message"]
        for i in range(3):
            messages |= chat.with_user(self.user_admin).message_post(body=f"msg {i}", message_type="comment")
        last_message = messages.sorted("id")[-1]
        # Discuss does not show user notifications, so they must not count as fetched
        self.env["mail.message"].create(
            {
                "model": chat._name,
                "res_id": chat.id,
                "message_type": "user_notification",
                "body": "notification",
                "partner_ids": [(4, self.partner_admin.id)],
                "reply_to": "test@example.com",
            }
        )
        member = chat.channel_member_ids.filtered(lambda m: m.partner_id == self.partner_employee)

        with self._search_spy() as spy:
            chat.with_user(self.user_employee).channel_fetched()

        self.assertEqual(self._search_limits(spy), [1], "channel_fetched must read only the last message")
        member.invalidate_recordset(["fetched_message_id"])
        self.assertEqual(member.fetched_message_id, last_message)

    def test_group_fetched_is_skipped(self):
        group = (
            self.env["discuss.channel"].with_user(self.user_employee).create_group(partners_to=[self.partner_admin.id])
        )
        group.with_user(self.user_admin).message_post(body="msg", message_type="comment")
        member = group.channel_member_ids.filtered(lambda m: m.partner_id == self.partner_employee)

        with self._search_spy() as spy:
            group.with_user(self.user_employee).channel_fetched()

        self.assertFalse(spy.called, "channel_fetched must not search the messages of a group")
        member.invalidate_recordset(["fetched_message_id"])
        self.assertFalse(member.fetched_message_id)
