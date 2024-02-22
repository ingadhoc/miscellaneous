from odoo import models, fields, api


class OkrObjective(models.Model):
    _name = 'okr.objective'
    _description = 'OKR Objectives'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    # _parent_store = True
    _order = 'from_date, department_id, to_date, name'

    name = fields.Char(required=True)
    description = fields.Char(required=True)
    notes = fields.Html()
    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)
    # parent_path = fields.Char(index=True, unaccent=False)
    # parent_id = fields.Many2one('okr.objective', index=True, ondelete='cascade', check_company=True)
    department_id = fields.Many2one('hr.department',)
    user_id = fields.Many2one('res.users', string='Responsible', required=True)
    key_result_ids = fields.One2many('okr.key_result', 'objective_id', string='Key Results')
    type = fields.Selection([('commitment', 'Commitment'), ('inspirational', 'Inspirational')], required=True)
    progress = fields.Integer(compute='_compute_progress', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('key_result_ids.progress', 'key_result_ids.weight')
    def _compute_progress(self):
        for rec in self:
            rec.progress = sum(x.progress * x.weight/100 for x in rec.key_result_ids)
