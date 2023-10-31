from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class OkrObjetivoLine(models.Model):
    _name = "okr.objetivo.line"
    _description = "Objetivo line"

    kr = fields.Char(string="Descripción KR", required=True, readonly=False)
    descripcion_ampliada = fields.Char(string="Descripcion ampliada", required=True, readonly=False)
    progreso = fields.Integer(string="Progress", default=0, store=True, readonly=False)
    peso = fields.Integer(string="Peso")
    comentarios = fields.Char()
    objetivo_padre = fields.Many2one('okr.objetivo')
    target = fields.Integer(string="Target")
    resultado = fields.Integer(string="Resultado")
    responsable = fields.Char()
    plan_de_accion = fields.Char()
    comentarios = fields.Char()
    interdependencias = fields.Char()
    realizado_en_el_q = fields.Char()
    notas_proximo_q = fields.Char()
    team = fields.Selection(related='objetivo_padre.team')
