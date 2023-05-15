from odoo import api, models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        if self.env.user.has_group('portal_timesheet.group_portal_backend_timesheet'):
            return super(Http, self.with_context(portal_bypass=True)).session_info()
        else:
            return super(Http, self).session_info()
