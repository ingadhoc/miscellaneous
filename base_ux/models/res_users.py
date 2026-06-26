##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        # res.partner only defaults tz from context['tz'] (the browser cookie
        # set on web login). Users created by scripts/provisioning get no such
        # context and are born with tz=False, which then clashes with the
        # required that hr enforces in Preferences. Fall back to the creator's
        # tz so tz is never empty.
        for vals in vals_list:
            if not vals.get("tz"):
                vals["tz"] = self.env.context.get("tz") or self.env.user.tz
        return super().create(vals_list)
