from odoo import models, fields, api

class OkrResult(models.Model):
    _name = 'okr.result'
    _description = 'Key Results for OKR'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'progress'

    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    user_id = fields.Many2one('res.users', string='Responsible')
    weight = fields.Float(string='Weight')
    target = fields.Float(string='Target')
    result = fields.Float()
    progress = fields.Float(string='Progress Percentage', compute='_compute_progress_percentage', store=True)
    company_id = fields.Many2one('res.company')
    objective_id = fields.Many2one('okr.objective', string='Objective', required=True)


    @api.depends('result', 'target')
    def _compute_progress_percentage(self):
        for result_okr in self:
            if result_okr.target:
                result_okr.progress = (result_okr.result / result_okr.target) * 100
            else:
                result_okr.progress = 0.0
