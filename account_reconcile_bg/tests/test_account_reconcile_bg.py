##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import (
    TestBankRecWidgetCommon,
)
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountReconcileBg(TestBankRecWidgetCommon):
    """Test que la conciliación se envía a background cuando hay muchas líneas."""

    def _create_test_invoices(self, count=10):
        """Crea facturas de prueba para conciliar."""
        invoices = self.env["account.move"]
        for i in range(count):
            invoice = self._create_invoice_line(
                "out_invoice",
                invoice_line_ids=[{"price_unit": 100.0}],
            )
            invoices |= invoice.move_id
        return invoices

    def test_sync_below_threshold(self):
        """Con pocas líneas (< threshold) debe procesar sincrónico."""
        self.env["ir.config_parameter"].sudo().set_param("account_reconcile_bg.lines_threshold", "3")

        # Crear facturas y línea de extracto (2 < 3 = sync)
        invoices = self._create_test_invoices(count=2)
        st_line = self._create_st_line(amount=200.0)

        # Contar jobs antes
        jobs_before = self.env["bg.job"].search_count([])

        # Crear widget y seleccionar facturas
        wizard = self.env["bank.rec.widget"].with_context(default_st_line_id=st_line.id).new({})

        # Simular selección de líneas
        invoice_lines = invoices.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        wizard.selected_aml_ids = invoice_lines

        # Validar NO debe crear job (2 < 3)
        jobs_after = self.env["bg.job"].search_count([])
        self.assertEqual(jobs_before, jobs_after, "No debe crear jobs en sync")

    def test_background_above_threshold(self):
        """Con muchas líneas (>= threshold) debe ir a background y ejecutar correctamente."""
        self.env["ir.config_parameter"].sudo().set_param("account_reconcile_bg.lines_threshold", "2")

        # Crear facturas y línea de extracto (3 >= 2 = background)
        invoices = self._create_test_invoices(count=3)
        st_line = self._create_st_line(amount=300.0)

        # Crear widget y seleccionar facturas
        wizard = self.env["bank.rec.widget"].with_context(default_st_line_id=st_line.id).new({})
        invoice_lines = invoices.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        wizard.selected_aml_ids = invoice_lines

        # Validar - debe crear job
        wizard._js_action_validate()

        # Buscar el job creado (por modelo, método y orden por fecha)
        job = self.env["bg.job"].search(
            [
                ("model", "=", "account.bank.statement.line"),
                ("method", "=", "_bg_validate_reconciliation"),
            ],
            order="create_date desc",
            limit=1,
        )
        self.assertTrue(job, "Debe crear un job en background")
        self.assertEqual(job.state, "enqueued", "El job debe estar encolado")
        self.assertTrue(st_line.reconciliation_in_background, "El flag debe estar activo")

        # Ejecutar el método directamente simulando el contexto que setea bg.job.run()
        selected_aml_ids = job.kwargs_json.get("selected_aml_ids", [])
        st_line.with_context(bg_job=True, bg_job_id=job.id)._bg_validate_reconciliation(
            selected_aml_ids=selected_aml_ids
        )

        # Verificar que el flag se limpió
        self.assertFalse(st_line.reconciliation_in_background, "El flag debe estar en False al terminar")

        # Verificar que la línea de extracto está conciliada
        self.assertTrue(st_line.is_reconciled, "La línea debe estar conciliada")

        # Verificar que las facturas están conciliadas
        for invoice in invoices:
            self.assertEqual(invoice.payment_state, "paid", f"La factura {invoice.name} debe estar pagada")
