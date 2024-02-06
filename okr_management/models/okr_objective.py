from odoo import models, fields, api

class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description = 'Objectives OKRs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'progress'

    name = fields.Char(string='Objective', required=True)
    description = fields.Text(string='Description')
    user_id = fields.Many2one('res.users', string='Responsible')
    quarter = fields.Selection(selection=[('q1','Q1'), ('q2','Q2'),('q3','Q3'),('q4','Q4'),])
    year = fields.Datetime(required=True)
    is_current_quarter = fields.Boolean(compute="_compute_is_current_quarter", store=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration_days', store=True)
    progress = fields.Float()
    okr_type = fields.Selection(selection=[('commitment','Commitment'), ('inspirational','Inspirational'),])
    company_id = fields.Many2one('res.company')

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

