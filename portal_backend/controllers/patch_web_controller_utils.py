from odoo.http import request
from odoo.addons.web.controllers import utils
import sys


# Monkey patch to bypass is internal check for portal users
def new_is_user_internal(uid):
    return request.env['res.users'].with_context(portal_bypass=True).browse(uid)._is_internal()


utils.is_user_internal = new_is_user_internal
sys.modules['odoo.addons.web.controllers.home'].is_user_internal = new_is_user_internal
sys.modules['odoo.addons.portal.controllers.web'].is_user_internal = new_is_user_internal
