##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    ncopies = fields.Integer(string="Number of print copies", default=1)

    @api.model
    def _get_rendering_context(self, docids, data):
        res = super()._get_rendering_context(docids, data)
        ncopies = self.ncopies
        if self._context.get('force_email', False):
            ncopies = 1
        res.update({
            'ncopies': ncopies,
        })
        return res

    @api.constrains('ncopies')
    def _check_ncopies(self):
        if self.filtered(lambda x: x.ncopies < 1):
            raise ValidationError(_("The number of copies must be strict positive and different than zero."))
