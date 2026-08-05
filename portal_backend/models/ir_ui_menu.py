from odoo import Command, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _register_hook(self):
        """Assert all parent menus has internal group."""
        # NOTE:
        # It is done on registry load, and not when loading menus, because that runs on read-only
        # requests. Registry is reloaded after installing modules, so this also captures the case
        # when portal_backend is already installed and the user installs another module with a
        # parent menu without internal group.
        parent_menus_wo_group = self.sudo().search([("parent_id", "=", False), ("group_ids", "=", False)])
        if parent_menus_wo_group:
            parent_menus_wo_group.with_context(from_config=True).write(
                {"group_ids": [Command.link(self.env.ref("base.group_user").id)]}
            )
        return super()._register_hook()
