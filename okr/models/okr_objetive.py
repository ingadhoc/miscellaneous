from odoo import api, models, fields


class OkrObjetives(models.Model):
    _name = 'okr.objetives'
    _description = "Objetives"

    name = fields.Char(required=True, copy=False)
    description = fields.Char()
    date_start = fields.Date(help="Fecha de inicio del objetivo.")
    date_stop = fields.Date(help="Fecha de fin del objetivo.")
    dependency_ids = fields.Many2one('hr.department')
