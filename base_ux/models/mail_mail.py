import smtplib

from odoo import models

class MailMail(models.Model):
    _inherit = 'mail.mail'

    def send(self, auto_commit=False, raise_exception=False):
        try:
            super().send(auto_commit=auto_commit, raise_exception=raise_exception)
        except smtplib.SMTPServerDisconnected:
            pass
