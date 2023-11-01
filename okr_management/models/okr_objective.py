from odoo import api, models, fields


class Objective(models.Model):
    _name: 'okr.objective'
    _description: 'okr.objective'

    name = fields.Char(required=True)
    description = fields.Char()

    company_id = fields.Many2one('res.company') # Agregar default
    department_id = fields.Many2one('hr.department')
    partner_id = fields.Many2one('res.partner', string="Responsible", required=True)

    progress = fields.Float(compute="_compute_progress")
    year = fields.Datetime(required=True) #Agregar por defecto año corriente
    quarter = fields.Selection(selection=[('st', '1'), ('nd', '2'), ('rd', '3'), ('th', '4')], required=True)
    is_commitment = fields.Boolean(default=False)
    is_current_quarter = fields.Boolean(compute="_compute_is_current_quarter", stored=True)
    comments = fields.Text()
    next_q_comments = fields.Text()


    def _compute_progress(self):
        pass

    def _compute_is_current_quarter(self):
        pass
