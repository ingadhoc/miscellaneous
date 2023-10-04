from odoo import models, fields


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    message_attachment_count = fields.Integer(
        groups="base.group_user, portal_backend.group_portal_backend")
    message_follower_ids = fields.One2many(
        groups="base.group_user, portal_backend.group_portal_backend")

    def _get_mail_thread_data(self, request_list):
        """ This avoids to get an error when an internal user is follower of a record that a portal_backend has access
        """
        if 'followers' in request_list and self.env.user.has_group('portal_backend.group_portal_backend'):
            request_list.remove('followers')
        return super()._get_mail_thread_data(request_list)
