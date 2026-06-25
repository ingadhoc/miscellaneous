from odoo import Command, models, tools


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @tools.ormcache_context("self._uid", "debug", keys=("lang",))
    def load_menus(self, debug):
        """Assert all parent menus has internal group."""
        # NOTE:
        # It is important to do it here to capture the case when portal_backend is already installed and the user
        # installs another module with a parent menu without internal group.
        parent_menus_wo_group = self.sudo().search([("parent_id", "=", False), ("groups_id", "=", False)])
        # Evitamos el write (y su clear_cache global) cuando no hay nada que corregir.
        # ir.ui.menu.write invalida el registry de forma incondicional; como load_menus
        # está cacheado, un write en cada llamada invalida su propio cache y genera una
        # tormenta de invalidaciones cross-worker en cada carga de menús.
        if parent_menus_wo_group:
            parent_menus_wo_group.with_context(from_config=True).write(
                {"groups_id": [Command.link(self.env.ref("base.group_user").id)]}
            )
        return super().load_menus(debug=debug)
