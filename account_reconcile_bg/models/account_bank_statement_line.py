##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    reconciliation_in_background = fields.Boolean(
        string="Reconciliation in Background",
        default=False,
        readonly=True,
        help="Indicates that this line is being reconciled in background",
    )

    def _bg_validate_reconciliation(self, selected_aml_ids=None):
        """
        Método ejecutado en background para validar la conciliación.
        Se llama desde el job de base_bg.

        :param selected_aml_ids: IDs de las líneas seleccionadas por el usuario
        """
        self.ensure_one()
        _logger = logging.getLogger(__name__)

        # Preparar datos para mensaje
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        st_line_url = f"{base_url}/odoo/account.bank.statement.line/{self.id}"
        st_line_name = self.name or f"Line {self.id}"

        try:
            # Crear el widget de conciliación
            wizard = self.env["bank.rec.widget"].with_context(default_st_line_id=self.id).new({})

            _logger.info(f"[BG] Wizard created for st_line {self.id}")

            # Agregar las líneas al widget correctamente usando el método interno
            if selected_aml_ids:
                amls = self.env["account.move.line"].browse(selected_aml_ids)
                wizard._action_add_new_amls(amls, allow_partial=False)

            # Ejecutar la validación con el context manager
            with wizard._action_validate_method():
                wizard._action_validate()

            # Retornar mensaje de éxito
            return Markup(
                _("Bank reconciliation completed successfully:<br><a href='%s' target='_blank'>%s</a>")
                % (st_line_url, st_line_name)
            )
        except Exception as e:
            return Markup(
                _("Bank reconciliation failed:<br><a href='%s' target='_blank'>%s</a><br><br>Error: %s")
                % (st_line_url, st_line_name, str(e))
            )
        finally:
            self.write({"reconciliation_in_background": False})

    @api.constrains(
        "amount",
        "amount_currency",
        "currency_id",
    )
    def _check_reconciliation_in_background(self):
        """Valida que no se modifiquen líneas en proceso de conciliación background."""
        if self.env.context.get("bg_job"):
            return
        for line in self:
            if line.reconciliation_in_background:
                raise UserError(
                    _(
                        "Cannot modify payment lines that are being reconciled in background. "
                        "Please wait until the reconciliation process is complete.\n"
                        "Journal Entry (id): %(entry)s (%(id)s)",
                        entry=line.move_id.name,
                        id=line.move_id.id,
                    )
                )
