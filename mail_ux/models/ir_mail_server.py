##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def action_send_test_mail(self):
        """Test the SMTP connection and, if successful, open the test mail wizard.

        Raises the native UserError if the connection test fails so the user
        sees the standard Odoo connection-error message.
        """
        self.ensure_one()
        # Test connection first; any UserError propagates natively to the UI
        self.test_smtp_connection()
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar mail de prueba"),
            "res_model": "mail.server.test.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_mail_server_id": self.id,
            },
        }
