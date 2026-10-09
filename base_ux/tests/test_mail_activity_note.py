from odoo.tests import Form, TransactionCase


class TestMailActivityNote(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test activity note"})
        cls.type_with_note = cls.env["mail.activity.type"].create(
            {"name": "Test type with note", "default_note": "<p>Default note</p>"}
        )
        cls.type_without_note = cls.env["mail.activity.type"].create({"name": "Test type without note"})

    def _new_activity_form(self):
        return Form(
            self.env["mail.activity"].with_context(
                default_res_model_id=self.env["ir.model"]._get_id("res.partner"),
                default_res_id=self.partner.id,
            ),
            view="mail.mail_activity_view_form_popup",
        )

    def test_written_note_is_kept_when_changing_type(self):
        with self._new_activity_form() as form:
            form.activity_type_id = self.type_without_note
            form.note = "<p>My own note</p>"
            form.activity_type_id = self.type_with_note
            self.assertIn("My own note", str(form.note))

    def test_empty_note_takes_default_note(self):
        with self._new_activity_form() as form:
            form.activity_type_id = self.type_without_note
            form.activity_type_id = self.type_with_note
            self.assertIn("Default note", str(form.note))
