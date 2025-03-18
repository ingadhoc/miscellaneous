import smtplib

from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        try:
            super().send(
                auto_commit=auto_commit, raise_exception=raise_exception, post_send_callback=post_send_callback
            )
        except smtplib.SMTPServerDisconnected:
            pass
