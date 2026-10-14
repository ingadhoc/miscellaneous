from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @api.ormcache("frozenset(self.env.user._get_group_ids())", "debug")
    def _visible_menu_ids(self, debug=False):
        """Hide the root menus without group, and their submenus, from external users."""
        visible_ids = super()._visible_menu_ids(debug)
        if self.env.user._has_group("base.group_user"):
            return visible_ids
        menus = self.sudo().browse(visible_ids)
        open_root_ids = set(menus.filtered(lambda menu: not menu.parent_id and not menu.group_ids).ids)
        if not open_root_ids:
            return visible_ids
        return frozenset(menu.id for menu in menus if self._portal_backend_root_id(menu) not in open_root_ids)

    @api.model
    def _portal_backend_root_id(self, menu):
        if menu.parent_path:
            return int(menu.parent_path.split("/")[0])
        # menus inserted by SQL have no parent_path
        while menu.parent_id:
            menu = menu.parent_id
        return menu.id
