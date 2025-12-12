from odoo import models, fields, api


class OkrManagement(models.Model):
    _name = 'ir.model.okr_management'
    _description = 'ir.model.okr_management'

    objective_summary = fields.Text()
    description_summary = fields.Text()
    progress = fields.Float()
    weight = fields.Float()
    target = fields.Float()
    result = fields.Float()
    responsible_ids = fields.One2many() # me falta relacionarlo con los usuarios 
    team_id = fields.One2many() # me fatla relacionarlo con los equipos
    action_plan = fields.Text()
    comments = fields.Text()
    interdependencies = fields.Text()
    made_in_the_quarter = fields.Text()
    notes_for_next_quarter = fields.Text()

    # Y falta todo lo otro...
