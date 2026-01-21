from odoo import models, fields, api

class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description = 'okr.objective'

    name = fields.Char(string='Resume', required=True)
    description = fields.Char(string='Description', required=True)
    objective_type = fields.Selection([('inspirational', 'Inspirational'), ('commitment', 'Commitment')], required=True, default='inspirational')
    kr_ids = fields.One2many('okr.kr', 'objective_id')
    progress = fields.Float(compute='_compute_progress')
    responsible_id = fields.One2many('hr.employee')
    teammate_ids = fields.Many2many('hr.employee')
    quarter_id = fields.Many2one('okr.quarter')
    #prefix_code = fields.Char()

    @api.depends('kr_ids.progress')
    def _compute_progress(self):
        for record in self:
            record.progress = 0 # TODO
