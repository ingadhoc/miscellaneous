from odoo import api, models
from odoo.tools import html2plaintext
from odoo.tools.safe_eval import safe_whitelist, wrap_module

RE_FUNCTIONS = ["escape", "findall", "fullmatch", "match", "search", "split", "sub", "subn"]
RE_FLAGS = ["A", "ASCII", "DOTALL", "I", "IGNORECASE", "M", "MULTILINE", "S"]

# Odoo checks every call made by evaluated code against this whitelist
for function in RE_FUNCTIONS:
    safe_whitelist.add_function(f"re.{function}")
safe_whitelist.add_instance("re.Match")


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    re = wrap_module(__import__("re"), RE_FUNCTIONS + RE_FLAGS)

    @api.model
    def _get_eval_context(self, action=None):
        """Enable re python library to regex search and html2plaintext function from odoo tools"""
        eval_context = super()._get_eval_context(action=action)
        eval_context.update(
            {
                "re": self.re,
                "html2plaintext": html2plaintext,
            }
        )
        return eval_context
