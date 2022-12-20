from odoo import models, fields


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    message_attachment_count = fields.Integer(
        groups="base.group_user, portal_backend.group_portal_backend")
    message_follower_ids = fields.One2many(
        groups="base.group_user, portal_backend.group_portal_backend")
