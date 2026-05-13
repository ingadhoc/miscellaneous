import smtplib
import ssl
from socket import gaierror

from odoo import _, fields, models
from odoo.exceptions import UserError


class MailServerTestWizard(models.TransientModel):
    _name = "mail.server.test.wizard"
    _description = "Wizard de prueba de servidor de correo saliente"

    mail_server_id = fields.Many2one(
        comodel_name="ir.mail_server",
        string="Servidor de correo saliente",
        required=True,
        context={"active_test": False},
    )
    email_to = fields.Char(
        string="Correo destinatario",
        required=True,
    )

    def action_send_test_mail(self):
        """Build and send a test email directly via SMTP, bypassing all
        Python-level sending guards (server_mode, mail neutralization, etc.).

        The bypass is achieved by calling ``ir.mail_server.connect()`` with
        ``allow_archived=True`` and then invoking ``smtp.send_message()``
        directly — never going through ``send_email()``, which is the layer
        where restrictions such as ``server_mode.allow_send_mail`` operate.
        """
        self.ensure_one()
        IrMailServer = self.env["ir.mail_server"]

        # Verify the user has read access on ir.mail_server before elevating.
        IrMailServer.check_access_rights("read")

        # Browse with active_test=False so archived servers (neutralized DBs)
        # are accessible, but without bypassing ACLs / record rules.
        mail_server = IrMailServer.with_context(active_test=False).browse(self.mail_server_id.id)
        if not mail_server.exists():
            raise UserError(
                _("No se encontró el servidor de correo. " "Por favor, recargue la página e intente de nuevo.")
            )
        mail_server.check_access_rule("read")
        mail_server = mail_server.sudo()

        email_from = mail_server._get_test_email_from()
        message = IrMailServer._build_email__(
            email_from=email_from,
            email_to=[self.email_to],
            subject=_("Prueba de mail desde Odoo"),
            body=_("Mail de prueba enviado desde mi base de Odoo. " "Por favor no responder."),
            subtype="plain",
        )

        smtp = None
        try:
            # allow_archived=True is critical for neutralized databases where
            # all real servers are deactivated by the neutralize process.
            smtp = IrMailServer._connect__(
                mail_server_id=mail_server.id,
                allow_archived=True,
            )
            if smtp:
                smtp.send_message(message)
        except (gaierror, TimeoutError) as e:
            raise UserError(
                _(
                    "No se pudo enviar el mail: Sin respuesta del servidor. " "Verifique la dirección y el puerto.\n%s",
                    e,
                )
            ) from e
        except smtplib.SMTPRecipientsRefused as e:
            raise UserError(
                _(
                    "No se pudo enviar el mail: El servidor rechazó la dirección destinataria.\n%s",
                    e,
                )
            ) from e
        except smtplib.SMTPException as e:
            raise UserError(_("No se pudo enviar el mail: %s", e)) from e
        except ssl.SSLError as e:
            raise UserError(_("No se pudo enviar el mail: Error de SSL.\n%s", e)) from e
        except Exception as e:
            raise UserError(_("No se pudo enviar el mail: %s", e)) from e
        finally:
            if smtp:
                try:
                    smtp.quit()
                except Exception:
                    pass

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("¡Mail de prueba enviado con éxito! " "Por favor, revise su casilla de correo."),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
