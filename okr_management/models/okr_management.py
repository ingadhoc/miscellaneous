from odoo import fields, models, api
from odoo.exceptions import UserError

class OkrManagement(models.Model):
    _name = 'okr.management'
    _description = 'Management of Adhoc okr'

    name = fields.Char()
    objective = fields.Text()
    user_ids = fields.Many2many(comodel_name='res.users')
    okr_type = fields.Selection(selection=[('insp', 'Inspirational'),('comm','Commitment')])
    progress = fields.Integer(compute='_compute_okr_progress', store=False)
    target = fields.Integer()
    result = fields.Float()
    action_plan = fields.Text()
    comments = fields.Text()

    def _compute_okr_progress(self):
        for rec in self:
            if rec.result and rec.target and rec.target != 0:
                rec.progress = (rec.result / rec.target) * 100
            else:
                rec.progress = 0
