from odoo import api, models, fields


class OkrKR(models.Model):
    _name = 'okr.kr'
    _description = "key results"

    name = fields.Char(required=True, copy=False)
    objective_id = fields.Many2one('okr.objetives', required=True)
    progress = fields.Float(compute="_compute_progress")
    weight = fields.Integer(required=True)
    target = fields.Integer(required=True)
    result = fields.Integer()
    user_id = fields.Many2one('res.users', required=True)
    user_ids = fields.Many2many('res.users')
    action_plan = fields.Char()
    comments = fields.Char()
    dependency_ids = fields.Many2many('hr.department')
    made_in_q = fields.Char()
    notes_next_q = fields.Char()

    @api.depends('result', 'target')
    def _compute_progress(self):
        for rec in self:
            if rec.result and rec.target:
                rec.progress = (rec.result / rec.target)*100
            else:
                rec.progress = False
