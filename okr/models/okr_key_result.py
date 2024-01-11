from odoo import models, fields, api
from datetime import date

class OkrKeyResult(models.Model):
    _name = 'okr.key.result'
    _description= 'OKR Key Result'

    name = fields.Char(required=True)
    description = fields.Char()
    responsible = fields.Many2one('res.users', required=True)
    objective = fields.Many2one('okr.objective', required=True)
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
    progress = fields.Float(compute="_compute_progress")
    comments = fields.Text()

    @api.depends('result', 'target')
    def _compute_progress(self):
        for rec in self:
            rec.progress = (rec.result / rec.target)*100
