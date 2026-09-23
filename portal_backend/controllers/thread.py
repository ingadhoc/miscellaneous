##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import http
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.http import request


class PortalBackendThreadController(ThreadController):
    @http.route("/mail/thread/data", methods=["POST"], type="json", auth="user")
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        """Core empties request_list for non internal users, so the chatter never gets
        followersCount nor attachments and its counters spin forever. Let portal backend users
        through: core still checks read access on the record before answering."""
        if request.env.user.has_group("portal_backend.group_portal_backend"):
            request.update_context(portal_bypass=True)
        return super().mail_thread_data(thread_model, thread_id, request_list, **kwargs)
