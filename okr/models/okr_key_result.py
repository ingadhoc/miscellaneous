from odoo import models, fields, api

class OkrKeyResult(models.Model):
    _name = 'okr.key_result'
    _description = 'OKR Key Result'

    name = fields.Char(required=True)
    description = fields.Text(required=True)
    department_id = fields.Many2one('hr.department')
    user_id = fields.Many2one('res.users', string= 'Responsible')
    objective_id = fields.Many2one('okr.objective')
    weight = fields.Integer()
    target = fields.Integer()
    result = fields.Integer()
    progress = fields.Float(compute = 'compute_progress', store=True, default=0)
    # state?
    # interdependencias
    # plan de acción
    # comentarios

    @api.depends('result','target')
    def _compute_progress(self):
        for rec in self:
            if rec.target !=0:
                rec.progress = (rec.result)/(rec.target)*100
            else:
                rec.progress = 0.0



