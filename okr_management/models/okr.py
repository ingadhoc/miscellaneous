##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################


from odoo import models, fields, api

class OKR(models.Model):
    _name = 'okr.okr'
    _description = 'Objectives and Key Results'

    name = fields.Char(string='Objective', required=True)
    description = fields.Text(string='Description')
    target_value = fields.Float(string='Target Value')
    quarter = fields.Selection(required=True)
    year = fields.Datetime(required=True)
    is_current_quarter = fields.Boolean(compute="_compute_is_current_quarter", store=True)
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
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration_days', store=True)


    @api.depends('current_value', 'target_value')
    def _compute_progress_percentage(self):
        for okr in self:
            if okr.target_value:
                okr.progress_percentage = (okr.current_value / okr.target_value) * 100
            else:
                okr.progress_percentage = 0.0
    
    @api.depends('quarter', 'year')
    def _compute_is_current_quarter(self):
        for okr in self:
            current_date = fields.Date.context_today(okr)
            current_quarter = (current_date.month - 1) // 3 + 1

            if (
                okr.quarter == current_quarter
                and okr.year == current_date.year
            ):
                okr.is_current_quarter = True
            else:
                okr.is_current_quarter = False

    @api.depends('start_date', 'end_date')
    def _compute_duration_days(self):
        for okr in self:
            if okr.start_date and okr.end_date:
                start_date = fields.Date.from_string(okr.start_date)
                end_date = fields.Date.from_string(okr.end_date)
                delta = end_date - start_date
                okr.duration_days = delta.days
            else:
                okr.duration_days = 0
