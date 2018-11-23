##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ResCountryState(models.Model):

    _inherit = 'res.country.state'

    _order = 'country_id,name'
