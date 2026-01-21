from odoo import models, fields

class OkrQuarter(models.Model):
    _name = 'okr.quarter'
    _description = 'okr.quarter'

    name = fields.Char(string='Quarter', required=True)
    description = fields.Char(string='Description', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    department_id = fields.One2many('hr.department')
    objective_ids = fields.One2many('okr.objective')
