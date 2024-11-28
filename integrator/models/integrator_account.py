from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odooly import Client
import logging
_logger = logging.getLogger(__name__)


class IntegratorAccount(models.Model):

    _name = 'integrator.account'
    _inherit = ['mail.composer.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Integration Account'
    _mailing_enabled = True

    name = fields.Char(required=True, tracking=True, store=True, compute='_compute_name', default=lambda self: _('New'))
    odoo_hostname = fields.Char("Hostname", required=True, tracking=True)
    odoo_db_name = fields.Char("Database Name", required=True, tracking=True)
    odoo_user = fields.Char("Username or E-Mail", required=True, tracking=True)
    odoo_password = fields.Char("Password", required=True,)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], copy=False, default='draft',
        required=True, tracking=True)
    channel_alias = fields.Char('Alias', default=False)

    @api.depends('odoo_db_name')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.odoo_db_name

    def back_to_draft(self):
        self.write({'state': 'draft'})

    def test_and_confirm(self):
        self.test_connection()
        self.write({'state': 'confirmed'})

    def test_connection(self):
        """ Odoo Connection Test.
        Returns True if successful.
        Raises a UserError otherwise.
        """
        self.ensure_one()
        try:
            # Attempt to get client
            client = self._odoo_get_client()
        except Exception as e:
            raise UserError("Unable to connect to Odoo. "
                            "The server responded: {}".format(str(e)))
        # Make sure version is correct
        self._odoo_ensure_version(client)
        # Notify Success
        result = "Connection with Odoo was successful!"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'type': 'success',
                'message': result,
                'sticky': False,
            }
        }

    def _odoo_get_client(self):
        self.ensure_one()
        try:
            return Client(
                # Use JSONRPC to prevent error when server responds with None
                self.odoo_hostname.strip("/") + "/jsonrpc",
                db=self.odoo_db_name,
                user=self.odoo_user,
                password=self.odoo_password,
            )
        except Exception as e:
            raise UserError("Unable to Connect to Database. Error: %s" % e)

    def _odoo_ensure_version(self, client):
        """ Makes sure Odoo version is supported
        """
        odoo_version = int(client.server_version.split(".")[0])
        if odoo_version < 13:
            raise UserError(
                "The Odoo version on the remote system is not supported. "
                "Please upgrade to v13.0 or higher")
        return True
