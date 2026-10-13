##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import json
from collections import defaultdict

from odoo import models
from odoo.addons.mail.models.mail_message import _find_allowed_doc_ids


class MailScheduledMessage(models.Model):
    _inherit = "mail.scheduled.message"

    def _compute_res_access(self):
        """Same as core, but checking the post access of the document (_mail_post_access) instead of write,
        as in 19.0: a user who can post on a record can schedule a message on it."""
        assert self.env.su
        if not self or not self.browse().sudo(False).has_access("read"):
            self.res_access = False
            return

        model_docid_msgids = defaultdict(lambda: defaultdict(list))
        for message in self:
            if message.model and message.res_id:
                model_docid_msgids[message.model][message.res_id].append(message.id)

        allowed = _find_allowed_doc_ids(self.env(su=False), model_docid_msgids, "create")
        for message in self:
            message.res_access = message.id in allowed

    def _post_message(self, raise_exception=True):
        """Resolve role_ids from notification_parameters into partner_ids before posting."""
        for scheduled_message in self:
            notification_params = json.loads(scheduled_message.notification_parameters or "{}")
            role_ids = notification_params.get("role_ids")
            if role_ids:
                role_partners = (
                    self.env["res.users"].sudo().search_fetch([("role_ids", "in", role_ids)], ["partner_id"]).partner_id
                )
                existing_partner_ids = set(scheduled_message.partner_ids.ids)
                new_partner_ids = role_partners.ids
                partners_to_add = [pid for pid in new_partner_ids if pid not in existing_partner_ids]
                if partners_to_add:
                    scheduled_message.sudo().write(
                        {
                            "partner_ids": [(4, pid) for pid in partners_to_add],
                        }
                    )
            scheduled_message._resolve_recipient_emails(notification_params)
        return super()._post_message(raise_exception=raise_exception)

    def _resolve_recipient_emails(self, notification_params):
        """Resolve the recipient emails sent by the chatter into partners, as /mail/message/post does."""
        self.ensure_one()
        creator = self.create_uid
        record = self.env[self.model].browse(self.res_id).with_user(creator)
        no_create = not creator.has_group("base.group_partner_manager")
        vals = {}
        for key, field in (("partner_emails", "partner_ids"), ("partner_cc_emails", "partner_cc_ids")):
            if emails := notification_params.get(key):
                partners = record._partner_find_from_emails_single(emails, no_create=no_create)
                if partners:
                    vals[field] = [(4, pid) for pid in partners.ids]
        if vals:
            self.sudo().write(vals)
