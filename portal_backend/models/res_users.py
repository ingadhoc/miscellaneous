##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_internal(self):
        self.ensure_one()
        if self.sudo().has_group("portal_backend.group_portal_backend") and self.env.context.get("portal_bypass"):
            return True
        return super()._is_internal()
