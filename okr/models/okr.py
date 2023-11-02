from odoo import models,fields
import datetime


class Okr(models.Model):
    _name = 'okr'
    _description= 'Gestión de Okrs'
    _order = "id desc"

    name= fields.Char(required=True)
    description = fields.Text()
    area = fields.Selection([('sistemas', 'Sistemas'),('ventas','Ventas')])
    number_q = fields.Integer()
    progress = fields.Float()
    peso = fields.Float()
    user_id = fields.Many2one('res.users', string='Responsable')
    # target
    # equipo
    # responsable
