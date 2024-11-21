from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class OkrObjetivoLine(models.Model):
    _name = "okr.key_result"
    _description = "OKR key result"
    _check_company_auto = True

    name = fields.Char(required=True)
    description = fields.Char(required=True)
    progress = fields.Integer(string="Progress", default=0, store=True)
    weight = fields.Integer()
    comments = fields.Char()
    objective = fields.Many2one('okr.objective')
    target = fields.Integer(string="Target")
    result = fields.Integer()
    user_id = fields.Many2one('res.users', string="Responsible")
    plan_de_accion = fields.Char()
    interdependencies = fields.Many2many('hr.department')
    realizado_en_el_q = fields.Char()
    notas_proximo_q = fields.Char()
