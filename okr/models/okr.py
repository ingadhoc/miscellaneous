from odoo import models,fields
from datetime import date

class OKR(models.Model):
    _name = 'okr'
    _description= 'Okr Management'

    name = fields.Char(required=True)
    description = fields.Char()
    company_id = fields.Many2one('res.company')
    responsible = fields.Many2one('res.users', required=True)
    date_start = fields.Date(required=True, default=date.today())
    date_end = fields.Date(required=True)
    priority = fields.Selection([
        ('very_high', 'Muy Alta'),
        ('high', 'ALta'),
        ('medium', 'Media'),
        ('low', 'Baja'),
        ('very_low', 'Muy Baja'),
    ], required=True)
    target = fields.Float(required=True)
    target_uom = fields.Selection([
        ('percentaje', '%'),
        ('units', 'Unidades'),
        ('score', 'Puntaje'),
        ('success', 'Casos de Éxito'),
        ('sla', 'SLA'),
        ('error', 'Errores'),
    ], string='Unit of Measure', required=True)
    result = fields.Float(required=True)
