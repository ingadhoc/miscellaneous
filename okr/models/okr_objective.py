from odoo import api, models, fields


class Objective(models.Model):
    _name = "okr.objective"
    _description = "OKR Objectives"

    name = fields.Char(required=True)
    display_name = fields.Char(compute="_compute_display_name")
    description = fields.Char()

    company_id = fields.Many2one('res.company') # Agregar default
    # department_id = fields.Many2one('hr.department')
    partner_id = fields.Many2one('res.partner', string="Responsible", required=True)

    progress = fields.Float(compute="_compute_progress")
    year = fields.Datetime(required=True) #Agregar por defecto año corriente
    quarter = fields.Selection(selection=[
        ('st', '1'),
        ('nd', '2'),
        ('rd', '3'),
        ('th', '4'),
    ], required=True)
    type = fields.Selection(selection=[
        ('commitment', 'Commitment'),
        ('inspirational', 'Inspirational'),
    ])
    is_commitment = fields.Boolean(compute="_compute_is_commitment", store=True)
    is_current_quarter = fields.Boolean(compute="_compute_is_current_quarter", store=True)
    comments = fields.Text()
    next_q_comments = fields.Text()


    @api.depends('name')
    def _compute_display_name(self):
        for objective in self:
            objective.display_name = f"[Q{objective.quarter.value}]: {objective.name}"

    def _compute_progress(self):
        pass

    def _compute_is_current_quarter(self):
        pass

    @api.depends('type')
    def _compute_is_commitment(self):
        for objective in self:
            if objective.type == 'commitment':
                objective.is_commitment = True
            else:
                objective.is_commitment = False
