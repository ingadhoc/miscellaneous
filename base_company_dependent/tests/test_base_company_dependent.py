##############################################################################
#
#    Copyright (C) 2024  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged

# Domain is available in Odoo 19+ (odoo.fields.Domain)


@tagged("-at_install", "post_install")
class TestBaseCompanyDependent(TransactionCase):
    """Tests para el módulo base_company_dependent.

    Valida los helpers de lectura/escritura JSONB cruda, la resolución de
    valores company_dependent por compañía, y la exposición del atributo
    ``company_dependent`` en las vistas.

    Se usa ``res.partner.barcode`` (Char, company_dependent) como campo de
    prueba, ya que está disponible en el módulo ``base`` sin dependencias
    adicionales.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.helper = cls.env["base.company.dependent"]

        # Dos compañías para probar valores multi-compañía
        cls.company_1 = cls.env.company
        cls.company_2 = cls.env["res.company"].create({"name": "Test Company 2"})

        # Un partner de prueba
        cls.partner = cls.env["res.partner"].create({"name": "CD Test Partner"})

        # Dar acceso al usuario a ambas compañías
        cls.env.user.company_ids = cls.company_1 | cls.company_2

    # ------------------------------------------------------------------
    # _get_raw_json / _write_raw_json
    # ------------------------------------------------------------------

    def test_get_raw_json_empty(self):
        """_get_raw_json devuelve {} cuando la columna JSONB es NULL o vacía."""
        raw = self.helper._get_raw_json("res_partner", "barcode", self.partner.id)
        self.assertIsInstance(raw, dict)

    def test_write_and_read_raw_json(self):
        """_write_raw_json persiste un dict JSONB que luego puede ser leído."""
        payload = {str(self.company_1.id): "BC-001"}
        self.helper._write_raw_json("res_partner", "barcode", self.partner.id, payload)

        raw = self.helper._get_raw_json("res_partner", "barcode", self.partner.id)
        self.assertEqual(raw.get(str(self.company_1.id)), "BC-001")

    def test_write_raw_json_multiple_companies(self):
        """_write_raw_json almacena claves por compañía independientemente."""
        payload = {
            str(self.company_1.id): "BC-C1",
            str(self.company_2.id): "BC-C2",
        }
        self.helper._write_raw_json("res_partner", "barcode", self.partner.id, payload)

        raw = self.helper._get_raw_json("res_partner", "barcode", self.partner.id)
        self.assertEqual(raw[str(self.company_1.id)], "BC-C1")
        self.assertEqual(raw[str(self.company_2.id)], "BC-C2")

    # ------------------------------------------------------------------
    # _resolve_m2o_display
    # ------------------------------------------------------------------

    def test_resolve_m2o_display_existing_record(self):
        """_resolve_m2o_display devuelve display_name para un registro existente."""
        result = self.helper._resolve_m2o_display("res.company", self.company_1.id)
        self.assertEqual(result, self.company_1.display_name)

    def test_resolve_m2o_display_false(self):
        """_resolve_m2o_display devuelve None si el ID es falsy."""
        self.assertIsNone(self.helper._resolve_m2o_display("res.company", False))
        self.assertIsNone(self.helper._resolve_m2o_display("res.company", 0))

    def test_resolve_m2o_display_nonexistent(self):
        """_resolve_m2o_display devuelve None si el registro no existe."""
        result = self.helper._resolve_m2o_display("res.company", 999999999)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # _get_field_static_domain
    # ------------------------------------------------------------------

    def test_get_field_static_domain_no_domain(self):
        """Campos sin domain devuelven Domain.TRUE."""
        field = self.env["res.partner"]._fields["barcode"]
        model_obj = self.env["res.partner"]
        result = self.helper._get_field_static_domain(field, model_obj)
        self.assertEqual(result, Domain.TRUE)

    def test_get_field_static_domain_list(self):
        """Un domain tipo list se convierte en Domain correctamente."""

        class FakeField:
            domain = [("active", "=", True)]

        result = self.helper._get_field_static_domain(FakeField(), self.env["res.partner"])
        self.assertEqual(list(result), [("active", "=", True)])

    def test_get_field_static_domain_string(self):
        """Un domain tipo string se parsea con ast.literal_eval."""

        class FakeField:
            domain = "[('active', '=', True)]"

        result = self.helper._get_field_static_domain(FakeField(), self.env["res.partner"])
        self.assertEqual(list(result), [("active", "=", True)])

    def test_get_field_static_domain_callable(self):
        """Un domain tipo callable se invoca y se convierte."""

        class FakeField:
            domain = staticmethod(lambda model: [("name", "!=", False)])

        result = self.helper._get_field_static_domain(FakeField(), self.env["res.partner"])
        self.assertEqual(list(result), [("name", "!=", False)])

    def test_get_field_static_domain_empty_string(self):
        """Un domain string vacío devuelve Domain.TRUE."""

        class FakeField:
            domain = ""

        result = self.helper._get_field_static_domain(FakeField(), self.env["res.partner"])
        self.assertEqual(result, Domain.TRUE)

    def test_get_field_static_domain_callable_error(self):
        """Un callable que lanza excepción devuelve Domain.TRUE."""

        class FakeField:
            @staticmethod
            def domain(model):
                raise RuntimeError("boom")

        result = self.helper._get_field_static_domain(FakeField(), self.env["res.partner"])
        self.assertEqual(result, Domain.TRUE)

    # ------------------------------------------------------------------
    # get_company_dependent_values  (Char field: barcode)
    # ------------------------------------------------------------------

    def test_get_company_dependent_values_no_specific(self):
        """Sin valores específicos, todas las compañías muestran is_specific=False."""
        result = self.helper.with_user(self.env.user).get_company_dependent_values(
            "res.partner", self.partner.id, "barcode"
        )
        self.assertIn("values", result)
        self.assertIn("field_type", result)
        self.assertEqual(result["field_type"], "char")
        self.assertIsNone(result["comodel_name"])

        for row in result["values"]:
            self.assertFalse(row["is_specific"])
            self.assertIn("company_id", row)
            self.assertIn("company_name", row)

    def test_get_company_dependent_values_with_specific(self):
        """Después de asignar un valor específico por compañía, is_specific=True."""
        # Escribimos un barcode para company_1 usando raw JSON
        payload = {str(self.company_1.id): "BC-SPEC"}
        self.helper._write_raw_json("res_partner", "barcode", self.partner.id, payload)

        result = self.helper.with_user(self.env.user).get_company_dependent_values(
            "res.partner", self.partner.id, "barcode"
        )
        values_by_company = {v["company_id"]: v for v in result["values"]}

        self.assertTrue(values_by_company[self.company_1.id]["is_specific"])
        self.assertFalse(values_by_company[self.company_2.id]["is_specific"])

    def test_get_company_dependent_values_non_cd_field_raises(self):
        """Pedir valores de un campo no company_dependent lanza ValueError."""
        with self.assertRaises(ValueError):
            self.helper.get_company_dependent_values("res.partner", self.partner.id, "name")

    def test_get_company_dependent_values_nonexistent_field_raises(self):
        """Pedir un campo inexistente lanza ValueError."""
        with self.assertRaises(ValueError):
            self.helper.get_company_dependent_values("res.partner", self.partner.id, "campo_inventado")

    # ------------------------------------------------------------------
    # set_company_dependent_values  (Char field: barcode)
    # ------------------------------------------------------------------

    def test_set_company_dependent_values_explicit(self):
        """set_company_dependent_values escribe un valor explícito por compañía."""
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "BC-SET-1"},
        )

        raw = self.helper._get_raw_json("res_partner", "barcode", self.partner.id)
        self.assertEqual(raw.get(str(self.company_1.id)), "BC-SET-1")

    def test_set_company_dependent_values_multiple_companies(self):
        """set_company_dependent_values puede escribir varias compañías a la vez."""
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {
                str(self.company_1.id): "BC-M1",
                str(self.company_2.id): "BC-M2",
            },
        )

        # Verificar leyendo con with_company
        partner_c1 = self.partner.with_company(self.company_1)
        partner_c2 = self.partner.with_company(self.company_2)
        self.assertEqual(partner_c1.barcode, "BC-M1")
        self.assertEqual(partner_c2.barcode, "BC-M2")

    def test_set_company_dependent_values_false(self):
        """Asignar False guarda un vacío explícito (la clave existe en el JSON)."""
        # Primero fijamos un valor
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "BC-THEN-CLEAR"},
        )
        # Luego asignamos False
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): False},
        )

        partner_c1 = self.partner.with_company(self.company_1)
        self.assertFalse(partner_c1.barcode)

    def test_set_company_dependent_values_reset(self):
        """'RESET' elimina la clave del JSON (restaura al fallback)."""
        # Fijamos un valor primero
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "BC-RESET-ME"},
        )

        raw_before = self.helper._get_raw_json("res_partner", "barcode", self.partner.id)
        self.assertIn(str(self.company_1.id), raw_before)

        # RESET
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "RESET"},
        )

        raw_after = self.helper._get_raw_json("res_partner", "barcode", self.partner.id)
        self.assertNotIn(str(self.company_1.id), raw_after)

    def test_set_company_dependent_values_non_cd_field_raises(self):
        """Escribir en un campo no company_dependent lanza ValueError."""
        with self.assertRaises(ValueError):
            self.helper.set_company_dependent_values(
                "res.partner", self.partner.id, "name", {str(self.company_1.id): "X"}
            )

    def test_set_company_dependent_values_returns_true(self):
        """set_company_dependent_values retorna True en éxito."""
        result = self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "BC-RET"},
        )
        self.assertTrue(result)

    # ------------------------------------------------------------------
    # get_company_dependent_meta
    # ------------------------------------------------------------------

    def test_get_company_dependent_meta_no_specific(self):
        """Sin valores específicos, meta indica is_specific=False para barcode."""
        meta = self.helper.get_company_dependent_meta("res.partner", self.partner.id)
        self.assertIn("barcode", meta)
        self.assertFalse(meta["barcode"])

    def test_get_company_dependent_meta_with_specific(self):
        """Con un valor específico, meta indica is_specific=True para barcode."""
        payload = {str(self.company_1.id): "BC-META"}
        self.helper._write_raw_json("res_partner", "barcode", self.partner.id, payload)

        meta = self.helper.with_user(self.env.user).get_company_dependent_meta("res.partner", self.partner.id)
        self.assertTrue(meta["barcode"])

    def test_get_company_dependent_meta_nonexistent_record(self):
        """Para un ID inexistente, meta retorna {}."""
        meta = self.helper.get_company_dependent_meta("res.partner", 999999999)
        self.assertEqual(meta, {})

    # ------------------------------------------------------------------
    # _get_field_domain_for_company
    # ------------------------------------------------------------------

    def test_get_field_domain_for_company_non_m2o_returns_empty(self):
        """Para un campo no Many2one (barcode es Char), devuelve []."""
        result = self.helper._get_field_domain_for_company("res.partner", "barcode", self.company_1.id)
        self.assertEqual(result, [])

    def test_get_field_domain_for_company_nonexistent_field(self):
        """Para un campo inexistente devuelve []."""
        result = self.helper._get_field_domain_for_company("res.partner", "campo_inventado", self.company_1.id)
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # _get_view_field_attributes (ir_ui_view.py)
    # ------------------------------------------------------------------

    def test_company_dependent_in_view_field_attributes(self):
        """El atributo 'company_dependent' está incluido en los field attributes
        expuestos al frontend, validando el override de ir_ui_view.py."""
        attrs = self.env["res.partner"]._get_view_field_attributes()
        self.assertIn("company_dependent", attrs)

    def test_view_field_attributes_preserves_base(self):
        """El override no rompe los atributos base de Odoo."""
        attrs = self.env["res.partner"]._get_view_field_attributes()
        for base_attr in ["type", "string", "readonly", "required", "domain"]:
            self.assertIn(base_attr, attrs)

    # ------------------------------------------------------------------
    # Integración: round-trip lectura → escritura → lectura
    # ------------------------------------------------------------------

    def test_roundtrip_set_then_get(self):
        """Verificación integral: escribir con set_ y leer con get_ es consistente."""
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {
                str(self.company_1.id): "BC-RT1",
                str(self.company_2.id): "BC-RT2",
            },
        )

        result = self.helper.with_user(self.env.user).get_company_dependent_values(
            "res.partner", self.partner.id, "barcode"
        )
        values_by_company = {v["company_id"]: v for v in result["values"]}

        self.assertTrue(values_by_company[self.company_1.id]["is_specific"])
        self.assertTrue(values_by_company[self.company_2.id]["is_specific"])

    def test_roundtrip_set_reset_then_get(self):
        """Escribir, luego RESET, y verificar que is_specific vuelve a False."""
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "BC-TMP"},
        )
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "RESET"},
        )

        result = self.helper.with_user(self.env.user).get_company_dependent_values(
            "res.partner", self.partner.id, "barcode"
        )
        values_by_company = {v["company_id"]: v for v in result["values"]}
        self.assertFalse(values_by_company[self.company_1.id]["is_specific"])

    def test_access_check_on_get(self):
        """get_company_dependent_values verifica acceso de lectura al modelo."""
        # Usar un modelo válido no debería lanzar error
        self.helper.get_company_dependent_values("res.partner", self.partner.id, "barcode")
        # No se espera excepción; si check falla, el test falla

    def test_access_check_on_set(self):
        """set_company_dependent_values verifica acceso de escritura al modelo."""
        # Usar un modelo válido no debería lanzar error
        self.helper.set_company_dependent_values(
            "res.partner",
            self.partner.id,
            "barcode",
            {str(self.company_1.id): "BC-ACC"},
        )

    def test_access_check_on_meta(self):
        """get_company_dependent_meta verifica acceso de lectura al modelo."""
        self.helper.get_company_dependent_meta("res.partner", self.partner.id)
