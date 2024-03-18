from odoo import models, fields


class KrPPal(models.Model):
    _name = "kr.ppal"
    _description = "Kr ppal"
    _rec_name = 'description'

    code = fields.Char(required=True)
    description = fields.Char(required=True)
