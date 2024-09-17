from odoo import api, fields, models

class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description = 'Okr objectives for current Q'

    name = fields.Char()
    description = fields.Char()
    date_start = fields.Date()
    date_end = fields.Date()
    teams_ids = fields.Many2one('hr.department')
