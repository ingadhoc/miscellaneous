from odoo import models, fields
from datetime import date

class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description= 'OKR Objective'

    name = fields.Char(required=True)
    description = fields.Char()
    company_id = fields.Many2one('res.company')
    responsible = fields.Many2one('res.users', required=True)
    date_start = fields.Date(required=True, default=date.today())
    date_end = fields.Date(required=True)
    type = fields.Selection([
        ('commitment', 'Commitment'),
        ('inspirational', 'Inspirational'),])
    comments = fields.Text()
