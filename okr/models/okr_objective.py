from odoo import models, fields

class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description = 'OKR Objectives'

    name = fields.Char(required=True)
    description = fields.Text(required=True)
    user_id = fields.Many2one('res.users', string= 'Responsible')
    progress = fields.Integer(default = 0)
    type = fields.Selection([('commitment', 'Commitment'),('inspirational', 'Inspirational')])
    quarter = fields.Selection([('q1', 'Q1'),('q2', 'Q2'),('q3', 'Q3'),('q4', 'Q4')])
    department_id = fields.Many2one('hr.department', required=True)
    key_result_ids = fields.One2many('okr.key_result', 'objective_id')
    notes = fields.Text()
    # state
    #compute = 'compute_progress'






