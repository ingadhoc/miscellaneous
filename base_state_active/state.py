# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class res_country_state(models.Model):
    _inherit = 'res.country.state'

    active = fields.Boolean(
        default=True,
    )
