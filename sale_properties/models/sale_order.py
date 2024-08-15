from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_properties = fields.Properties(string='Properties', definition='team_id.team_propertied_definition', copy=True)
