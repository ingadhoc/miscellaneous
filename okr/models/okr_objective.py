from odoo import models, fields


class OkrObjective(models.Model):
    _name = 'okr.objective'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Okr Objective'
    _order = 'progress'

    name = fields.Char(string='Objective', required=True)
    description = fields.Text()
    user_id = fields.Many2one('res.users', string='Responsible')
    progress = fields.Float()
    okr_type = fields.Selection(selection=[('commitment', 'Commitment'), ('inspirational', 'Inspirational'),])
    company_id = fields.Many2one('res.company')
