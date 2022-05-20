# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):

        """ Portal users are not allow to access to attachments
        """
        if self.env.user.has_group('base.group_portal'):
            super(IrAttachment, self.sudo()).check(mode=mode, values=values)
