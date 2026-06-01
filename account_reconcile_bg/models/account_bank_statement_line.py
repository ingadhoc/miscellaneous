##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    reconciliation_in_background = fields.Boolean(
        string="Reconciliation in Background",
        readonly=True,
        help="Indicates that this line is being reconciled in background",
    )

    def set_batch_payment_bank_statement_line(self, batch_payment_id):
        self.ensure_one()

        if self.env.context.get("account_reconcile_bg_skip"):
            return super().set_batch_payment_bank_statement_line(batch_payment_id)

        if self.reconciliation_in_background:
            raise UserError(
                _("This reconciliation is already being processed in background. Please wait until it finishes.")
            )

        batch_payment = self.env["account.batch.payment"].browse(batch_payment_id)
        threshold = int(self.env["ir.config_parameter"].sudo().get_param("account_reconcile_bg.lines_threshold", "100"))
        if len(batch_payment.payment_ids) < threshold:
            return super().set_batch_payment_bank_statement_line(batch_payment_id)

        self._enqueue_batch_reconciliation(batch_payment_id)

    def _enqueue_batch_reconciliation(self, batch_payment_id):
        self.write({"reconciliation_in_background": True})
        self.env.flush_all()

        try:
            self.env["base.bg"].bg_enqueue_records(
                self,
                "_bg_set_batch_payment_bank_statement_line",
                threshold=1,
                name=_("Bank Reconciliation: %s") % self.name,
                priority=5,
                batch_payment_id=batch_payment_id,
            )
        except Exception:
            self.write({"reconciliation_in_background": False})
            raise

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

    def _bg_set_batch_payment_bank_statement_line(self, batch_payment_id=None):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        st_line_url = f"{base_url}/odoo/account.bank.statement.line/{self.id}"
        st_line_name = self.name or f"Line {self.id}"

        try:
            self.with_context(account_reconcile_bg_skip=True).set_batch_payment_bank_statement_line(batch_payment_id)
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

    @api.constrains("amount", "amount_currency", "currency_id")
    def _check_reconciliation_in_background(self):
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
