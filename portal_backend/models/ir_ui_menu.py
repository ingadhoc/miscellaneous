from odoo import models, Command


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def load_menus(self, debug):
        """ Assert all parent menus has internal group
        """
        parent_menus_wo_group = self.search([('parent_id', '=', False), ('groups_id', '=', False)])
        parent_menus_wo_group.write({
            'groups_id': [Command.link(self.env.ref('base.group_user').id)]
        })
        return super().load_menus(debug=debug)
