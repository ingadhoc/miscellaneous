from odoo import models, fields

class SaleOrder(models.Model):

    _inherit = 'sale.order'


    sale_order_properties = fields.Properties(
        'Properties', definition='team_id.sale_order_properties_definition', 
        copy=True)
