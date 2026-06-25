# For copyright and license notices, see __manifest__.py file in module root
# directory
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestLoadMenusCache(TransactionCase):
    """load_menus is cached by ormcache; it must not invalidate the registry on
    every call. ir.ui.menu.write clears the whole registry unconditionally, so
    writing on each load_menus invalidates its own cache and produces an
    invalidation storm under repeated screen reloads.
    """

    def _load_menus_clear_cache_calls(self):
        # force a cache miss so load_menus actually runs
        self.env.registry.clear_cache()
        with patch.object(type(self.env.registry), "clear_cache") as mock_clear:
            self.env["ir.ui.menu"].load_menus(False)
        return mock_clear.call_count

    def test_no_invalidation_when_no_root_menu_without_group(self):
        """With every root menu already having a group, load_menus must not write
        (and therefore must not invalidate the registry cache)."""
        menus = self.env["ir.ui.menu"].sudo()
        wo_group = menus.search([("parent_id", "=", False), ("groups_id", "=", False)])
        wo_group.write({"groups_id": [Command.link(self.env.ref("base.group_user").id)]})

        self.assertEqual(
            self._load_menus_clear_cache_calls(),
            0,
            "load_menus must not invalidate the registry cache when there are no "
            "root menus without an internal group.",
        )
