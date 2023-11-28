from odoo import models
from odoo.tools.safe_eval import wrap_module


class BaseExceptionMethod(models.AbstractModel):
    _inherit = "base.exception.method"

    def _exception_rule_eval_context(self, rec):
        time = wrap_module(__import__('time'), ['time', 'strptime', 'strftime', 'sleep', 'gmtime'])
        eval_context = super()._exception_rule_eval_context(rec)
        eval_context.update({
            'time': time,
        })
        return eval_context
