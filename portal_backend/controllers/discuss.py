from odoo import _, http
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.exceptions import UserError
from odoo.http import request


class PortalBackendAttachmentController(AttachmentController):
    @http.route("/mail/attachment/delete", methods=["POST"], type="jsonrpc", auth="public")
    def mail_attachment_delete(self, access_token_by_attachment_id, keep_on_messages=False, **kwargs):
        if request.env.user.has_group("portal_backend.group_portal_backend"):
            raise UserError(_("You are not allowed to remove attachments"))
        return super().mail_attachment_delete(
            access_token_by_attachment_id, keep_on_messages=keep_on_messages, **kwargs
        )
