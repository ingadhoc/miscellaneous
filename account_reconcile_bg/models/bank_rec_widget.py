##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, models
from odoo.exceptions import UserError


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    def _js_action_validate(self):
        """
        Override para procesar conciliaciones grandes en background.
        Si hay muchas líneas (> threshold), usa base_bg para procesarlo en 2do plano.
        """
        self.ensure_one()

        # Verificar si ya está procesando en background
        if self.st_line_id.reconciliation_in_background:
            raise UserError(
                _("This reconciliation is already being processed in background. Please wait until it finishes.")
            )

        # Invalidar caché y refrescar para obtener el estado actual desde la BD
        self.selected_aml_ids.invalidate_recordset(fnames=["reconciliation_in_background"])

        # Verificar si alguna de las líneas seleccionadas ya está en background (en cualquier extracto)
        lines_in_bg = self.selected_aml_ids.filtered("reconciliation_in_background")
        if lines_in_bg:
            raise UserError(
                _(
                    "Some of the selected payment lines (%s) are already being reconciled in background on another statement. "
                    "Please wait until they finish or select different lines."
                )
                % len(lines_in_bg)
            )

        # Obtener el umbral de líneas desde parámetros del sistema (default: 50)
        threshold = int(self.env["ir.config_parameter"].sudo().get_param("account_reconcile_bg.lines_threshold", "50"))

        # Contar las líneas seleccionadas para conciliar
        lines_count = len(self.selected_aml_ids)

        # DEBUG: Log para verificar

        # Si hay pocas líneas, ejecutar el proceso normal de manera sincrónica
        if lines_count < threshold:
            return super()._js_action_validate()

        # Si hay muchas líneas, procesar en background
        return self._validate_in_background()

    def _validate_in_background(self):
        """
        Encola la validación de conciliación en background usando base_bg.
        Nota: Como bank.rec.widget no se persiste, encolamos usando st_line_id.
        """
        self.ensure_one()

        _logger = logging.getLogger(__name__)

        # Marcar la línea de extracto y las líneas de pago como procesando en background
        self.st_line_id.write({"reconciliation_in_background": True})
        self.selected_aml_ids.write({"reconciliation_in_background": True})

        # Flush para asegurar que los cambios se escriben inmediatamente en la BD
        # Esto previene condiciones de carrera donde otro usuario podría conciliar las mismas líneas
        self.env.flush_all()

        # Capturar los IDs antes de encolar
        selected_ids = self.selected_aml_ids.ids
        _logger.info(f"[account_reconcile_bg] Capturing selected_aml_ids: {selected_ids}")

        try:
            # Encolar el job usando la línea de extracto (modelo persistente)
            _action, _jobs = self.env["base.bg"].bg_enqueue_records(
                self.st_line_id,
                "_bg_validate_reconciliation",
                threshold=1,  # Un job por línea
                name=_("Bank Reconciliation: %s") % self.st_line_id.name,
                priority=5,  # Alta prioridad
                selected_aml_ids=selected_ids,  # Pasar solo los IDs (lista de enteros)
            )
            _logger.info("[account_reconcile_bg] Job enqueued successfully")
        except Exception:
            # Si falla al encolar, limpiar los flags
            self.st_line_id.write({"reconciliation_in_background": False})
            self.selected_aml_ids.write({"reconciliation_in_background": False})
            raise

        # Enviar notificación al usuario usando el bus
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "type": "success",
                "message": _(
                    "This reconciliation is being processed in background. You will be notified when it's done."
                ),
            },
        )

        # Configurar el comando para el widget
        self.return_todo_command = {"done": True}

        # Retornar vacío - el widget usa return_todo_command
        return

    def _do_validate(self):
        """
        Método que ejecuta la validación real en background.
        Se llama desde el job de base_bg.
        """
        self.ensure_one()
        # Ejecutar la validación usando el método context manager
        with self._action_validate_method():
            self._action_validate()
