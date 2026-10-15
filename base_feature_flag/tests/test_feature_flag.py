import os
from unittest.mock import patch

from odoo import api
from odoo.addons.base_feature_flag import flag, is_on
from odoo.tests.common import TransactionCase, new_test_user


class Dummy:
    def __init__(self, env):
        self.env = env

    @flag("demo", "_run_v2")
    def run(self, value):
        return f"v1 {value}"

    def _run_v2(self, value):
        return f"v2 {value}"


class TestFeatureFlag(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="feature_flag_user", groups="base.group_user")
        cls.user_env = cls.env(user=cls.user)

    def _set_param(self, value):
        self.env["ir.config_parameter"].set_param("saas_feature.demo", value)

    def test_param_switches_variant_without_admin_rights(self):
        dummy = Dummy(self.user_env)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SAAS_FEATURE_DEMO", None)
            self.assertEqual(dummy.run("a"), "v1 a")
            self._set_param("1")
            self.assertTrue(is_on(self.user_env, "demo"))
            self.assertEqual(dummy.run("a"), "v2 a")
            self._set_param("0")
            self.assertEqual(dummy.run("a"), "v1 a")

    def test_environment_wins_over_param(self):
        self._set_param("0")
        with patch.dict(os.environ, {"SAAS_FEATURE_DEMO": "true"}):
            self.assertEqual(Dummy(self.env).run("b"), "v2 b")
        self._set_param("1")
        with patch.dict(os.environ, {"SAAS_FEATURE_DEMO": "no"}):
            self.assertEqual(Dummy(self.env).run("b"), "v1 b")

    def test_empty_environment_falls_back_to_param(self):
        self._set_param("yes")
        with patch.dict(os.environ, {"SAAS_FEATURE_DEMO": ""}):
            self.assertTrue(is_on(self.env, "demo"))

    def test_keeps_odoo_decorator_attributes(self):
        @flag("demo", "_variant")
        @api.model
        def outer(self):
            return True

        @api.model
        @flag("demo", "_variant")
        def inner(self):
            return True

        self.assertTrue(getattr(outer, "_api_model", False))
        self.assertTrue(getattr(inner, "_api_model", False))
