from odoo import Command, api, models, tools


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache("self.env.uid", "debug", "self.env.lang")
    def load_menus(self, debug):
        """Assert all parent menus has internal group."""
        # NOTE:
        # It is important to do it here to capture the case when portal_backend is already installed and the user
        # installs another module with a parent menu without internal group.
<<<<<<< 0c5498eb72cc07d99c005d8c8b202a16bf485c8a
        parent_menus_wo_group = self.sudo().search([("parent_id", "=", False), ("group_ids", "=", False)])
        parent_menus_wo_group.with_context(from_config=True).write(
            {"group_ids": [Command.link(self.env.ref("base.group_user").id)]}
        )
||||||| 8dce76a9220667566be9bb2a88419bd34864ecec
        parent_menus_wo_group = self.sudo().search([("parent_id", "=", False), ("groups_id", "=", False)])
        parent_menus_wo_group.with_context(from_config=True).write(
            {"groups_id": [Command.link(self.env.ref("base.group_user").id)]}
        )
=======
        parent_menus_wo_group = self.sudo().search([("parent_id", "=", False), ("groups_id", "=", False)])
        # Evitamos el write (y su clear_cache global) cuando no hay nada que corregir.
        # ir.ui.menu.write invalida el registry de forma incondicional; como load_menus
        # está cacheado, un write en cada llamada invalida su propio cache y genera una
        # tormenta de invalidaciones cross-worker en cada carga de menús.
        if parent_menus_wo_group:
            parent_menus_wo_group.with_context(from_config=True).write(
                {"groups_id": [Command.link(self.env.ref("base.group_user").id)]}
            )
>>>>>>> 512364a2b733efd66c81657f360d683bd2e71806
        return super().load_menus(debug=debug)
