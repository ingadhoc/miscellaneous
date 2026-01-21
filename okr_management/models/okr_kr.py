from odoo import models, fields, api

class OkrKr(models.Model):
    _name = 'okr.kr'
    _description = 'okr.kr'

    name = fields.Char(string='Resume', required=True)
    description = fields.Char(string='Description', required=True)
    objective_id = fields.Many2one('okr.objective', required=True)
    progress = fields.Float(string='Progress', compute='_compute_progress')
    importance = fields.Float(string='Importante')
    target = fields.Float(string='Target')
    result = fields.Float(string='Result')
    responsible_id = fields.One2many('hr.employee')
    teammate_ids = fields.Many2many('hr.employee')
    action_plan = fields.Text(string='Action Plan')
    #code = fields.Char(size=4, required=True)

    @api.depends('importance', 'result')
    def _compute_progress(self):
        for record in self:
            record.progress = 100 if self.result >= self.target else self.result / self.target

