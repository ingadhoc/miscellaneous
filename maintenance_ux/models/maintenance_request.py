##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = ["rating.mixin", "maintenance.request"]

    def action_send_rating(self):
        rating_template = self.env.ref("maintenance_ux.mail_template_maintenance_request_rating")
        for order in self:
            order.rating_send_request(rating_template, force_send=True)

    def _rating_get_operator(self):
        """Overwrite since we have user_ids and not user_id"""
        requests_with_one_user = self.filtered(
            lambda request: len(request.user_ids) == 1 and request.user_ids.partner_id
        )
        return requests_with_one_user.user_ids.partner_id or self.env["res.partner"]

    def _rating_get_partner(self):
        if self.create_uid.partner_id:
            return self.create_uid.partner_id
        return self.env["res.partner"]
