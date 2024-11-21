from odoo import models, fields, api


class OkrKeyResult(models.Model):
    _name = 'okr.key_result'
    _description = 'OKR Key Result'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    description = fields.Html()
    objective_id = fields.Many2one('okr.objective', required=True, ondelete='cascade')
    department_ids = fields.Many2many('hr.department', string='Interdependencies')
    user_id = fields.Many2one('res.users', string='Responsible', required=True)
    weight = fields.Integer(required=True)
    target = fields.Integer(required=True)
    result = fields.Integer()
    progress = fields.Integer(compute='_compute_progress', store=True)
    company_id = fields.Many2one(related='objective_id.company_id', store=True)

    @api.depends('result', 'target')
    def _compute_progress(self):
        for rec in self:
            rec.progress = rec.result / rec.target * 100 if rec.target else 100
