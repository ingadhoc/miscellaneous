from odoo import fields, models


class OkrBase(models.AbstractModel):

    _name = 'okr.base'
    _description = 'OKR Base'

    name = fields.Char()
    description = fields.Text()
    progress = fields.Integer()
    comments = fields.Text()


class OkrPlan(models.Model):

    _name = 'okr.plan'
    _description = 'OKR Plan By Year'

    name = fields.Char()  # TODO auto compute with the year of the related quarters.
    quarter_ids = fields.One2many('okr.quarter', 'plan_id')  # Auto group by date?


class OkrQuarter(models.Model):

    _name = 'okr.quarter'
    _description = 'OKR Quarter'

    plan_id = fields.Many2one('okr.plan')
    scope = fields.Selection([('global', 'Global'), ('area', 'Area')], required=True)
    department_id = fields.Many2one('hr.department')

    # TODO improve to manage period
    name = fields.Char(required=True)  # TODO Improve use display_name, Q1, Q2, Q3. Auto compute with dates?
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)

    okr_ids = fields.One2many('okr.objective', 'quarter_id', string="OKRs")
    half_q_presentation = fields.Char()
    final_q_presentation = fields.Char()


class OkrObjective(models.Model):

    _name = 'okr.objective'
    _description = 'OKR Objective'
    _inherit = 'okr.base'

    quarter_id = fields.Many2one('okr.quarter')
    weight = fields.Selection([
        ('commitment', 'Commitment'),
        ('inspiracional', 'Inspiracional'),
    ])
    kr_ids = fields.One2many('okr.kr', 'objective_id')


class OkrKr(models.Model):

    _name = 'okr.kr'
    _description = 'OKR KR'

    _inherit = 'okr.base'

    objective_id = fields.Many2one('okr.objective')
    weight = fields.Integer()
    target = fields.Integer()
    result = fields.Integer()
    responsible_id = fields.Many2one('hr.employee')
    team_ids = fields.Many2many('hr.employee')
    interdependencies = fields.Text()
    action_plan = fields.Text()
    url_task_file = fields.Char()
    notes_next_q = fields.Text()
