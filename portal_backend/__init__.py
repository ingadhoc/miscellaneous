##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, SUPERUSER_ID, Command

from . import models
from . import controllers

def post_init(cr, registry):
    """ Add internal users group to menu items
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    env['ir.ui.menu'].search([("groups_id", "=", False), ("parent_id", "=", False)]).write({
        'groups_id': [Command.link(env.ref('base.group_user').id)]
    })
