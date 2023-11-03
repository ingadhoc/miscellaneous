from odoo import models, fields


class OkrObjective(models.Model):
    _name = 'okr.key_result'
    _description = 'OKR Key Result'

    name = fields.Char(required=True)
    description = fields.Html()
    objective_id = fields.Many2one('okr.objective', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Responsible')
    weight = fields.Integer(required=True)
    target = fields.Integer(required=True)
    progress = fields.Integer()
