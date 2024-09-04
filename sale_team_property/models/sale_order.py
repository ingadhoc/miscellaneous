from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    properties = fields.Properties('Sale Order Properties',  
                                   definition='team_id.sale_order_properties_definition', 
                                   copy=True)
