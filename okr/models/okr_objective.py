from odoo import models, api, fields
import time
from odoo.exceptions import UserError


class OkrObjetivo(models.Model):
    _name = "okr.objective"
    _description = "OKR Objective"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _rec_name = 'name'

    name = fields.Many2one('kr.ppal', required=True)
    description = fields.Char(required=True)
    department_id = fields.Many2one('hr.department')
    progress = fields.Integer(string="Progress", compute='_compute_progress',help="Progress from zero knowledge (0%) to fully mastered (100%).", default=0, store=True)
    weight = fields.Selection([('inspiracional', 'Inspiracional'), ('commitment', 'Commitment')])
    comments = fields.Char()
    key_result_ids = fields.One2many('okr.key_result', 'objective')
    period = fields.Selection([('q1', 'Q1'), ('q2', 'Q2'), ('q3', 'Q3'), ('q4', 'Q4')], required=True)
    year = fields.Char(
        required=True,
        default=time.strftime('%Y'),
    )
    user_id = fields.Many2one('res.users', string="Responsible")
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
        help="Company for whose invoices the mandate can be used.")

    @api.depends('key_result_ids')
    def _compute_progress(self):
        sumatory = sum(self.key_result_ids.mapped('progress')) or 0
        self.progress = sumatory
        if sumatory > 100:
            raise UserError("The sum of the objectives progress can´t be higher than 100")
