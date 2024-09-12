from odoo import models, fields, api
from odoo.exceptions import UserError

class OkrKeyResult(models.Model):
    _name = 'okr.key.result'
    _description = 'Okr Key Result'

    name = fields.Char()
    description = fields.Text()
    objective =fields.Text()
    user_ids = fields.Many2one(
        'res.users',
    )
    progress= fields.Integer(
        compute='_compute_okr_progress',
        store = False,
    )
    importance = fields.Integer()#importancia dentro del kr
    target = fields.Integer()#objetivo esperado

    @api.depends('peso', 'target')
    def _compute_okr_progress(self):
        #mejorar codigo
        prog = 0
        for rec in self:
            if rec.importance and rec.target:
                prog = rec.importance