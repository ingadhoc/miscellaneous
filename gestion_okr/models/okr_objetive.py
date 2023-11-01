from odoo import api, models, fields


class OkrObjetives(models.Model):
    _name = 'okr.objetives'
    _description = "Objetives"

    name = fields.Char(required=True, copy=False, string='Nombre de objetivo')
    description = fields.Char(string='Descripcion')
    date_start = fields.Date(string='Fecha de inicio', help="Fecha de inicio del objetivo.")
    date_stop = fields.Date(string='Fecha de fin', help="Fecha de fin del objetivo.")
    department_id = fields.Many2one('hr.department', string="Departamento del objetivo")

