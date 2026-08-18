from odoo import Command, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _register_hook(self):
        """Assert all parent menus have internal group.

        NOTE:
        It is done on registry load to capture the case when portal_backend is already installed and the user
        installs another module with a parent menu without internal group.
        It can not be done while loading the menus: that route is readonly, so writing there breaks its cursor
        with "cannot execute INSERT in a read-only transaction" (the request is retried with a read/write one,
        but the failed query is already logged as an error).
        """
        super()._register_hook()
        parent_menus_wo_group = self.sudo().search([("parent_id", "=", False), ("group_ids", "=", False)])
        if parent_menus_wo_group:
            parent_menus_wo_group.with_context(from_config=True).write(
                {"group_ids": [Command.link(self.env.ref("base.group_user").id)]}
            )
