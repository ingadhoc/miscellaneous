##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDynamicMessage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.company = Partner.create({"name": "Dynamic Company", "function": "Supplier"})
        cls.person = Partner.create({"name": "Dynamic Person"})
        # child of the supplier: matches only the second line
        cls.employee = Partner.create({"name": "Dynamic Employee", "parent_id": cls.company.id})

    def test_dynamic_message_flow(self):
        """Dado un mensaje dinámico sobre contactos con dos líneas, cuando se
        confirma, entonces cada contacto muestra solo los mensajes cuyo dominio
        cumple, en una alerta del tipo elegido sobre su formulario.

        Cubre: vista a heredar por defecto, depends desde el dominio, la
        expresión "EXP:" en el código de la línea, el campo y la vista que crea
        confirm(), el cálculo por registro y la reconfirmación.
        """
        with Form(self.env["ir.model.dynamic_message"]) as dm_form:
            dm_form.name = "Test"
            dm_form.model_id = self.env["ir.model"]._get("res.partner")
            dm_form.alert_type = "warning"
            with dm_form.line_ids.new() as line:
                line.domain = '[("function", "=", "Supplier")]'
                line.message = "<p>Is a supplier</p>"
            with dm_form.line_ids.new() as line:
                line.domain = (
                    '[("parent_id.function", "=", "Supplier"), '
                    '("create_date", "<=", "EXP: datetime.datetime.now()"), ("id", "!=", 0)]'
                )
                line.message = "<p>Belongs to a supplier</p>"
        dm = dm_form.record

        with self.subTest("toma como vista a heredar el formulario principal del modelo"):
            self.assertEqual(dm.view_to_inherit_id, self.env.ref("base.view_partner_form"))

        with self.subTest("el depends junta los campos del dominio de las líneas"):
            self.assertEqual(set(dm.depends.split(",")), {"function", "parent_id", "create_date"})

        with self.subTest("la línea con EXP: deja la expresión sin comillas en el código"):
            code = dm.line_ids[1].code
            self.assertIn('("create_date", "<=", datetime.datetime.now())', code)
            self.assertNotIn("EXP:", code)

        dm.confirm()
        field_name = f"x_dynamic_message_{dm.id}"

        with self.subTest("confirmar crea el campo y la vista con la alerta del tipo elegido"):
            self.assertRecordValues(dm.field_id, [{"name": field_name, "ttype": "html", "state": "manual"}])
            self.assertEqual(dm.view_id.inherit_id, dm.view_to_inherit_id)
            self.assertIn("alert-warning", dm.view_id.arch_db)
            arch = self.env["res.partner"].get_views([(dm.view_to_inherit_id.id, "form")])["views"]["form"]["arch"]
            self.assertIn(f'<field name="{field_name}"', arch)

        with self.subTest("cada registro muestra solo los mensajes cuyo dominio cumple"):
            self.assertEqual(self.company[field_name], "<ul><li>Is a supplier</li></ul>")
            self.assertEqual(self.employee[field_name], "<ul><li>Belongs to a supplier</li></ul>")
            self.assertFalse(self.person[field_name])

        with self.subTest("reconfirmar con otro tipo de alerta actualiza la vista sin crear otro campo"):
            field, view = dm.field_id, dm.view_id
            dm.alert_type = "danger"
            dm.confirm()
            self.assertEqual(dm.field_id, field)
            self.assertEqual(dm.view_id, view)
            self.assertIn("alert-danger", view.arch_db)
            self.assertEqual(
                self.env["ir.model.fields"].search_count([("model", "=", "res.partner"), ("name", "=", field_name)]), 1
            )
