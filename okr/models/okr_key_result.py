from odoo import api, models, fields


class KeyResult(models.Model):
    _name = "okr.key_result"
    _description = "OKR Key Result"

    name = fields.Char(required=True)
    description = fields.Char()

    objective_id = fields.Many2one('okr.objective')
    partner_id = fields.Many2one('res.partner', string="Responsible", required=True)

    company_id = fields.Many2one('res.company', related="objective_id.company_id", store=True)
    # department_id = fields.Many2one('hr.department', related="objective_id.department_id", store=True)
    # depends_department_ids = fields.Many2many('hr.department')
    quarter = fields.Selection(related="objective_id.quarter", required=True)
    year = fields.Datetime(related="objective_id.year", required=True)
    is_commitment = fields.Boolean(related="objective_id.is_commitment")
    is_current_quarter = fields.Boolean(related="objective_id.is_current_quarter")

    weighing = fields.Float(required=True)
    target = fields.Float(required=True)
    result = fields.Float(required=True, default=0)
    progress = fields.Float(compute="_compute_progress")

    comments = fields.Text()
    next_q_comments = fields.Text()

    def _compute_progress(self):
        pass

    def _compute_is_current_quarter(self):
        pass
