from odoo import fields, models


class IotDevice(models.Model):
    _inherit = "iot.device"

    # print_node_api_key = fields.Char('Print Node API Key', readonly=True)
    connection = fields.Selection(
        selection_add=[("printnode_printer", "Print Node Printer")],
        ondelete={"printnode_printer": "set null"},
    )
