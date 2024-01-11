from odoo import models, fields, api


class OKR(models.Model):
    _name = 'okr.okr'
    _description = 'Objectives and Key Results'

    name = fields.Char(string='Objective', required=True)
    description = fields.Text(string='Description')
    target_value = fields.Float(string='Target Value')
    current_value = fields.Float(string='Current Value')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    progress_percentage = fields.Float(string='Progress Percentage', compute='_compute_progress_percentage', store=True)

    @api.depends('current_value', 'target_value')
    def _compute_progress_percentage(self):
        for okr in self:
            if okr.target_value:
                okr.progress_percentage = (okr.current_value / okr.target_value) * 100
            else:
                okr.progress_percentage = 0.0
