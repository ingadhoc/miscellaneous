from odoo import models, fields


class Team(models.Model):
    _inherit = 'crm.team'

    team_propertied_definition = fields.PropertiesDefinition('Team properties')
