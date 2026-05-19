##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestBasePartnerMerge(TransactionCase):
    def test_merge_partners_with_duplicated_followers(self):
        partner_model = self.env["res.partner"]
        followers_model = self.env["mail.followers"].sudo()
        subtype_comment = self.env.ref("mail.mt_comment")
        subtype_note = self.env.ref("mail.mt_note")

        document_partner = partner_model.create({"name": "Document partner"})
        src_partner = partner_model.create({"name": "Source partner", "email": "merge@test.example.com"})
        extra_src_partner = partner_model.create({"name": "Extra source", "email": "merge@test.example.com"})
        dst_partner = partner_model.create({"name": "Destination partner", "email": "merge@test.example.com"})

        followers_model.create(
            [
                {
                    "res_model": document_partner._name,
                    "res_id": document_partner.id,
                    "partner_id": src_partner.id,
                    "subtype_ids": [Command.set(subtype_comment.ids)],
                },
                {
                    "res_model": document_partner._name,
                    "res_id": document_partner.id,
                    "partner_id": extra_src_partner.id,
                    "subtype_ids": [Command.set(subtype_note.ids)],
                },
                {
                    "res_model": document_partner._name,
                    "res_id": document_partner.id,
                    "partner_id": dst_partner.id,
                },
            ]
        )

        merge_form = Form(
            self.env["base.partner.merge.automatic.wizard"].with_context(
                active_model="res.partner",
                active_ids=(src_partner | extra_src_partner | dst_partner).ids,
            )
        )
        merge_form.dst_partner_id = dst_partner
        merge_wizard = merge_form.save()

        merge_wizard.action_merge()

        self.assertFalse(src_partner.exists())
        self.assertFalse(extra_src_partner.exists())
        self.assertTrue(dst_partner.exists())

        merged_followers = followers_model.search(
            [
                ("res_model", "=", document_partner._name),
                ("res_id", "=", document_partner.id),
                ("partner_id", "in", [src_partner.id, extra_src_partner.id, dst_partner.id]),
            ]
        )

        self.assertEqual(len(merged_followers), 1)
        self.assertEqual(merged_followers.partner_id, dst_partner)
        self.assertSetEqual(set(merged_followers.subtype_ids.ids), {subtype_comment.id, subtype_note.id})
