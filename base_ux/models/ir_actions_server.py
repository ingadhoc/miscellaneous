from odoo import models, api
from odoo.tools import html2plaintext
import re
import pdb

class IrActionsServer(models.Model):

    _inherit = 'ir.actions.server'

    @api.model
    def _get_eval_context(self, action=None):
        """ Enable re python library to regex search and html2plaintext function from odoo tools """
        eval_context = super()._get_eval_context(action=action)
        eval_context.update({
            're': re,
            'html2plaintext': html2plaintext,
            'pdb_set_trace' : pdb.set_trace,
        })
        return eval_context
