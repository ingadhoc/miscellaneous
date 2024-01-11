from odoo import models, fields, api
from odoo.exceptions import UserError

class OkrManagement(models.Model):
    _name = 'okr.management'
    _description = 'Okr management'

    name = fields.Char()
    description = fields.Text()
    user_ids = fields.Many2many(
        comodel_name='res.users',
    )
    progress= fields.Integer(
        compute='_compute_okr_progress',
        store = False,
    )
    result = fields.Float()
    action_plan = fields.Text()
    comments = fields.Text()

    def _compute_okr_progress(self):
        for okr in self:
            if not okr.progress:
                prog = 0
            elif okr.progress:
                okr.progress = okr.progress
            elif self.progress < 0 or self.progress > 100:
                raise UserError('Valor de progreso invalido')
            else:
                prog = 0
        okr.progress = prog
