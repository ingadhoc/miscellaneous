##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class PortalWizard(models.TransientModel):
    _inherit = "portal.wizard"

    def action_grant_access_all(self):
        for wizard_user in self.user_ids:
            if not wizard_user.is_portal and not wizard_user.is_internal and wizard_user.email_state == "ok":
                wizard_user.action_grant_access()
        return self._action_open_modal()
