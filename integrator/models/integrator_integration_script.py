import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import test_expr, _SAFE_OPCODES


_logger = logging.getLogger(__name__)

DEFAULT_CODE = """# Available Context:
# - db2: Odoo Remote Client Database
# - Warning: Use "raise Warning('text')" to show a dialog box with the given
# text as parameter. Useful for debugging the script before activating the
# integration.
# - last_cron_execution: A datetime object with the last successful execution
# of the script.
# - time, datetime, dateutil, timezone: Useful Python libraries
# - context: A dictionary with information about current user, timezone, etc
# - sync_model(target_db, model_name, common_fields=None, boolean_fields=None, m2o_fields=None, m2m_fields=None, domain=[], sort="id", offset=0, limit=None, target_model_name=None)
#
# If you want to log the script's result as a message, assign something
# different than False to the "result" variable.
result = False
"""


class IntegratorIntegrationScript(models.Model):

    _name = "integrator.integration.script"
    _description = "integrator.integration.script"

    name = fields.Char(required=True)
    code = fields.Text(default=DEFAULT_CODE, required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "code" in values:
                self._script_test(code=values["code"])
        res = super().create(values)
        return res

    def write(self, values):
        if "code" in values:
            self._script_test(code=values["code"])
        res = super().write(values)
        return res

    def _script_test(self, code):
        try:
            test_expr(code, _SAFE_OPCODES, mode="exec")
        except Exception as e:
            raise UserError(e)
        return True
