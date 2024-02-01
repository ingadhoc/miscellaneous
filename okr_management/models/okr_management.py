from odoo import models, fields, api
from odoo.exceptions import UserError

class OkrManagement(models.Model):
    _name = 'okr.management'
    _description = 'Okr management'

    name = fields.Char()
    description = fields.Text()
    user_ids = fields.Many2many(
        comodel_name='res.users',
    )
    progress= fields.Integer(
        compute='_compute_okr_progress',
        store = False,
    )
    okr_type = fields.Selection(
        selection=[
            ('commitment', 'Commitment'),
            ('inspiracional', 'Inspiracional'),
        ],
    )
    result = fields.Float()
    action_plan = fields.Text()
    comments = fields.Text()
