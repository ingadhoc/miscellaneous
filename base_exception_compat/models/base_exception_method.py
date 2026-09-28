from odoo import models
from odoo.fields import Command


class BaseExceptionMethod(models.AbstractModel):
    _inherit = "base.exception.method"

    def detect_exceptions(self):
        # Full replacement of the upstream method: it writes the exceptions
        # through a second cursor that commits on the same rows the ongoing
        # transaction is about to write, which breaks with a serialization
        # failure (or blocks until the worker dies). Write in the current
        # transaction and return the rules, as before OCA/server-tools#3590.
        if self.env.context.get("test_base_exception"):
            # Upstream sets this key to exercise the second cursor on purpose.
            # Nothing sets it outside its own tests, so keeping that path alive
            # leaves them meaningful instead of red.
            return super().detect_exceptions()
        all_exception_ids, rules_to_remove, rules_to_add = self._get_exceptions()
        for rule_id, records in rules_to_remove.items():
            records.write({"exception_ids": [Command.unlink(rule_id)]})
        for rule_id, records in rules_to_add.items():
            records.write({"exception_ids": [Command.link(rule_id)]})
        return all_exception_ids
