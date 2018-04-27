from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    tx_adhoc_url = fields.Char(
        string="Transifex Adhoc URL",
        help="Configured transifex project for our modules")
    tx_oca_url = fields.Char(
        string="Transifex OCA URL",
        help="Configure transifex project for OCA modules")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            tx_adhoc_url=get_param('transifex_ux.tx_adhoc_url'),
            tx_oca_url=get_param('transifex_ux.tx_oca_url'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('transifex_ux.tx_adhoc_url', self.tx_adhoc_url)
        set_param('transifex_ux.tx_oca_url', self.tx_oca_url)
