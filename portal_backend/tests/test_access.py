##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestAccess(TransactionCase):
    """Portal Backend reaches the same records as in 19.0, not every record of the models it can access."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_pb = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create({"name": "access_pb", "login": "access_pb", "access_type": "portal_backend"})
        )
        cls.other = new_test_user(cls.env, login="access_other")
        cls.param = cls.env["ir.config_parameter"].sudo().search([], limit=1)
        cls.attachment_private = cls.env["ir.attachment"].create(
            {"name": "private.txt", "raw": b"secret", "res_model": "ir.config_parameter", "res_id": cls.param.id}
        )
        cls.attachment_own = cls.env["ir.attachment"].with_user(cls.user_pb).create({"name": "own.txt", "raw": b"mine"})

    def test_attachment_of_inaccessible_record(self):
        attachment = self.attachment_private.with_user(self.user_pb)
        for operation in ("read", "write"):
            with self.assertRaises(AccessError):
                attachment.check_access(operation)
        self.assertNotIn(self.attachment_private, self.env["ir.attachment"].with_user(self.user_pb).search([]))

    def test_own_attachment(self):
        attachment = self.attachment_own.with_user(self.user_pb)
        attachment.check_access("read")
        attachment.check_access("write")
        with self.assertRaises(AccessError):
            attachment.check_access("unlink")

    def test_private_channel(self):
        channel = (
            self.env["discuss.channel"]
            .with_user(self.other)
            ._get_or_create_chat([self.env.ref("base.partner_admin").id])
        )
        with self.assertRaises(AccessError):
            channel.with_user(self.user_pb).check_access("read")

    def test_activity_of_others(self):
        activity = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("res.partner"),
                "res_id": self.env.ref("base.partner_admin").id,
                "user_id": self.other.id,
                "date_deadline": fields.Date.today(),
            }
        )
        self.assertNotIn(activity, self.env["mail.activity"].with_user(self.user_pb).search([]))

    def test_internal_subtype(self):
        subtypes = self.env["mail.message.subtype"].with_user(self.user_pb).search([])
        self.assertTrue(subtypes)
        self.assertFalse(subtypes.filtered("internal"))
