from odoo import _, http
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.exceptions import UserError
from odoo.http import request


class PortalBackendAttachmentController(AttachmentController):
    @http.route("/mail/attachment/delete", methods=["POST"], type="jsonrpc", auth="public")
    def mail_attachment_delete(self, attachment_id, access_token=None, **kwargs):
        if request.env.user.has_group("portal_backend.group_portal_backend"):
            raise UserError(_("You are not allowed to remove attachments"))
        return super().mail_attachment_delete(attachment_id, access_token=access_token, **kwargs)
