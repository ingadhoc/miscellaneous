##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AddIotPrintnode(models.TransientModel):
    _name = "add.iot.printnode"
    _description = "Add IoT PrintNode"

    name = fields.Char(
        required=True,
    )
    print_node_api_key = fields.Char(
        required=True,
    )

    def action_add_iot_printnode_box(self):
        self.ensure_one()
        iot_box = (
            self.env["iot.box"]
            .sudo()
            .create(
                {
                    "name": self.name,
                    "print_node_api_key": self.print_node_api_key,
                    "token": self.print_node_api_key,
                }
            )
        )
        iot_box.action_print_update_devices()

        return {
            "type": "ir.actions.act_window",
            "res_model": "iot.box",
            "res_id": iot_box.id,
            "view_mode": "form",
            "target": "current",
        }
