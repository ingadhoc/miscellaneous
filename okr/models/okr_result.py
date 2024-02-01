from odoo import models, fields, api


class OkrResult(models.Model):
    _name = 'okr.result'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Okr Result'
    _order = 'progress'

    name = fields.Char(string='Title')
    description = fields.Text()
    user_id = fields.Many2one('res.users', string='Responsible')
    objective_id = fields.Many2one('okr.objective')
    weight = fields.Float()
    target = fields.Float()
    result = fields.Float()
    progress = fields.Float(compute="_compute_progress")
    department_ids = fields.Many2many('hr.department')
    company_id = fields.Many2one('res.company', related="objective_id.company_id", store=True)

    @api.depends('result', 'target')
    def _compute_progress(self):
        filtered_okr = self.filtered(lambda x: x.result and x.target)
        for rec in filtered_okr:
            rec.progress = (rec.result / rec.target) * 100
        (self - filtered_okr).progress = 0
