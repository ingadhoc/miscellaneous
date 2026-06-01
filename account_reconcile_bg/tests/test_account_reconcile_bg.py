##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.addons.account_accountant_batch_payment.tests.test_batch_payment import TestBatchPayment
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountReconcileBg(TestBatchPayment):
    def _create_batch_payment(self, payment_count):
        payments = self.env["account.payment"]
        for _ in range(payment_count):
            payments |= self.create_payment(self.partner_a, 100.0)
        result = payments.create_batch_payment()
        return self.env["account.batch.payment"].browse(result["res_id"])

    def test_sync_below_threshold(self):
        self.env["ir.config_parameter"].sudo().set_param("account_reconcile_bg.lines_threshold", "3")

        batch = self._create_batch_payment(payment_count=2)
        st_line = self._create_st_line(amount=200.0)

        jobs_before = self.env["bg.job"].search_count([])
        st_line.set_batch_payment_bank_statement_line(batch.id)

        self.env.flush_all()
        st_line.invalidate_recordset()
        self.assertEqual(self.env["bg.job"].search_count([]), jobs_before)
        self.assertTrue(st_line.is_reconciled)

    def test_background_above_threshold(self):
        self.env["ir.config_parameter"].sudo().set_param("account_reconcile_bg.lines_threshold", "2")

        batch = self._create_batch_payment(payment_count=3)
        st_line = self._create_st_line(amount=300.0)

        st_line.set_batch_payment_bank_statement_line(batch.id)

        job = self.env["bg.job"].search(
            [
                ("model", "=", "account.bank.statement.line"),
                ("method", "=", "_bg_set_batch_payment_bank_statement_line"),
            ],
            order="create_date desc",
            limit=1,
        )
        self.assertTrue(job)
        self.assertEqual(job.state, "enqueued")
        self.assertTrue(st_line.reconciliation_in_background)

        job.write({"state": "running"})
        with patch.object(job.env.cr, "commit", return_value=None):
            job.run()

        self.env.flush_all()
        st_line.invalidate_recordset()
        self.assertFalse(st_line.reconciliation_in_background)
        self.assertTrue(st_line.is_reconciled)
