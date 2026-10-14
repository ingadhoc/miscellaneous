##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests.common import TransactionCase


class TestMenus(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user_regular = cls.env.ref("base.group_user_regular")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.user_pb = Users.create({"name": "menus_pb", "login": "menus_pb", "access_type": "portal_backend"})
        cls.user_internal = Users.create({"name": "menus_int", "login": "menus_int", "access_type": "internal"})
        cls.Menu = cls.env["ir.ui.menu"]
        cls.action = cls.env["ir.actions.act_window"].create({"name": "Partners", "res_model": "res.partner"})

    def _visible(self, user):
        menus = self.Menu.with_user(user)
        return menus.browse(menus._visible_menu_ids())

    def _tree(self, **root_vals):
        root = self.Menu.create({"name": "Root", **root_vals})
        child = self.Menu.create(
            {"name": "Child", "parent_id": root.id, "action": f"ir.actions.act_window,{self.action.id}"}
        )
        return root, child

    # -- regular tier --------------------------------------------------------
    def test_portal_backend_user_is_not_regular(self):
        self.assertNotIn(self.group_user_regular.id, self.user_pb._get_group_ids())
        self.assertNotIn(self.env.ref("mail.menu_root_discuss"), self._visible(self.user_pb))

    def test_portal_backend_user_multi_company_is_not_regular(self):
        """Several companies add base.group_multi_company, which implies the regular tier."""
        company = self.env["res.company"].create({"name": "Second company"})
        self.user_pb.write({"company_ids": [Command.link(company.id)]})
        self.assertIn(self.env.ref("base.group_multi_company"), self.user_pb.all_group_ids)
        self.assertNotIn(self.group_user_regular.id, self.user_pb._get_group_ids())
        self.assertNotIn(self.env.ref("mail.menu_root_discuss"), self._visible(self.user_pb))

    def test_internal_user_keeps_regular(self):
        self.assertIn(self.group_user_regular.id, self.env.ref("base.user_admin")._get_group_ids())

    # -- root menus without group --------------------------------------------
    def test_root_menu_without_group_hidden_with_submenus(self):
        root, child = self._tree()
        self.assertFalse(root.group_ids, "nothing is written in the menu")
        visible = self._visible(self.user_pb)
        self.assertNotIn(root, visible)
        self.assertNotIn(child, visible)
        self.assertIn(child, self._visible(self.user_internal))

    def test_root_menu_with_group_visible(self):
        _root, child = self._tree(group_ids=[Command.set(self.env.ref("portal_backend.group_portal_backend").ids)])
        self.assertIn(child, self._visible(self.user_pb))

    def test_root_menu_restored_without_group(self):
        root, child = self._tree(active=False)
        root.active = True
        self.assertNotIn(child, self._visible(self.user_pb))

    def test_root_menu_loses_its_only_group(self):
        group = self.env["res.groups"].create({"name": "Menu group"})
        self.user_pb.write({"group_ids": [Command.link(group.id)]})
        _root, child = self._tree(group_ids=[Command.set(group.ids)])
        self.assertIn(child, self._visible(self.user_pb))
        group.unlink()
        self.assertNotIn(child, self._visible(self.user_pb))

    def test_menu_without_parent_path(self):
        _root, child = self._tree()
        self.env.cr.execute("UPDATE ir_ui_menu SET parent_path = NULL WHERE id = %s", [child.id])
        self.Menu.invalidate_model(["parent_path"])
        self.env.transaction.invalidate_ormcache()
        self.assertNotIn(child, self._visible(self.user_pb))
