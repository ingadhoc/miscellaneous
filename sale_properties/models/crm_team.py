from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    so_properties_definition = fields.PropertiesDefinition('Properties Definition')
