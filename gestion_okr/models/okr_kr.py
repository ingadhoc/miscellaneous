from odoo import api, models, fields


class OkrKR(models.Model):
    _name = 'okr.kr'
    _description = "key results"

    name = fields.Char(required=True, copy=False, string='Nombre del kr')
    objective_id = fields.Many2one('okr.objetives', string="Objetivo del kr", required=True)
    progress = fields.Float(string='Progreso',compute="_compute_progress")
    weight = fields.Integer(string='Peso', required=True)
    target = fields.Integer(string='Target', required=True)
    result = fields.Integer(string="Resultados")
    user_id = fields.Many2one('res.users', string="Responsable del kr", required=True)
    user_ids = fields.Many2many('res.users', string="Interesados")
    action_plan = fields.Char(string="Plan de acción")
    comments = fields.Char(string="Comentarios")
    dependencies = fields.Many2many('hr.department', string="Interdependencias con otras áreas")
    made_in_q = fields.Char(string="Realizados en el Q")
    notes_next_q = fields.Char(string="Notas para el próximo Q")

    @api.depends('result', 'target')
    def _compute_progress(self):
        for rec in self:
            if rec.result and rec.target:
                rec.progress = (rec.result / rec.target)*100
            else:
                rec.progress = False