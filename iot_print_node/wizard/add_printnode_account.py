##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AddPrintnodeAccount(models.TransientModel):
    _name = "add.printnode.account"
    _description = "Add PrintNode Account"

    name = fields.Char(
        required=True,
    )
    print_node_api_key = fields.Char(
        required=True,
    )

    def action_add_printnode_account(self):
        self.ensure_one()
        account = self.env["printnode.account"].create(
            {
                "name": self.name,
                "print_node_api_key": self.print_node_api_key,
            }
        )
        account.action_print_update_devices()

        return {
            "type": "ir.actions.act_window",
            "res_model": "printnode.account",
            "res_id": account.id,
            "view_mode": "form",
            "target": "current",
        }
