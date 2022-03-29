from odoo import models, api
from odoo.tools import html2plaintext
from odoo.tools.safe_eval import wrap_module

class IrActionsServer(models.Model):

    _inherit = 'ir.actions.server'

    re = wrap_module(__import__('re'), [])

    @api.model
    def _get_eval_context(self, action=None):
        """ Enable re python library to regex search and html2plaintext function from odoo tools """
        eval_context = super()._get_eval_context(action=action)
        eval_context.update({
            're': self.re,
            'html2plaintext': html2plaintext,
        })
        return eval_context
