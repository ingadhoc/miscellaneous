from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):

        """ Portal users are not allow to access to attachments
        """
        if self.env.user.has_group('portal_backend.group_portal_backend'):
            super(IrAttachment, self.with_context(portal_bypass=True)).check(mode, values)
        else:
            super(IrAttachment, self).check(mode, values)
