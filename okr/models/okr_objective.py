from odoo import models, fields


class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description = 'OKR Objectives'

    name = fields.Char(required=True)
    description = fields.Char(required=True)
    notes = fields.Html()
    department_id = fields.Many2one('hr.department', required=True,)
    user_id = fields.Many2one('res.users', string='Responsible')
    key_result_ids = fields.One2many('okr.key_result', 'objective_id', string='Responsible')
    type = fields.Selection([('commitment', 'Commitment'), ('inspirational', 'Inspirational')], required=True)
    progress = fields.Integer(compute='_compute_progress')

    def _compute_progress(self):
        # TODO impleemntar
        self.progress = 0.0
