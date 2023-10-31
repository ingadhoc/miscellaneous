from odoo import models, fields


class KrPPal(models.Model):
    _name = "kr.ppal"
    _description = "Kr ppal"
    _rec_name = 'descripcion'

    codigo = fields.Char(required=True)
    descripcion = fields.Char(required=True)
