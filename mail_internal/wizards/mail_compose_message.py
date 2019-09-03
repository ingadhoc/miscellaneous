from odoo import fields, models, api


class MailComposeMessage(models.TransientModel):

    _inherit = 'mail.compose.message'

    is_internal = fields.Boolean(
        'Send Internal Message',
        help='Whether the message is only for employees',
    )

    @api.multi
    def send_mail(self, auto_commit=False):
        internal = self.env.ref("mail_internal.mt_internal_message").id
        self.filtered(lambda x: x.is_internal).write({
            'subtype_id': internal,
            'is_log': False,
        })
        return super().send_mail(auto_commit=auto_commit)
