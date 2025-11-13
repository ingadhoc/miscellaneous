from odoo import models, fields


class CrmTeam(models.Model):

    _inherit = 'crm.team'


    sale_order_properties_definition = fields.PropertiesDefinition('Sale Order Properties')


