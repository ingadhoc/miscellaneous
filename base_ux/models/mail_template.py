##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    active = fields.Boolean(
        track_visibility='onchange',
        default=True,
    )
