##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class MaintenanceRequest(models.Model):
    _name = 'maintenance.request'
    _inherit = ['maintenance.request', 'rating.mixin']

    def action_send_rating(self):
        rating_template = self.env.ref('maintenance_ux.mail_template_maintenance_request_rating')
        for order in self:
            order.rating_send_request(rating_template, force_send=True)

    def _rating_get_partner(self):
        if self.create_uid.partner_id:
            return self.create_uid.partner_id
        return self.env['res.partner']
