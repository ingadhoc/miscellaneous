##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta
from unittest.mock import patch

from odoo import fields, tools
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBgJob(TransactionCase):
    def setUp(self):
        """Prepare environment references and keep cron timeout to restore later."""
        super(TestBgJob, self).setUp()
        self.BgJob = self.env["bg.job"]
        self._limit_time_real_cron = tools.config.get("limit_time_real_cron", 120)

    def tearDown(self):
        """Restore original cron timeout and teardown TransactionCase."""
        tools.config["limit_time_real_cron"] = self._limit_time_real_cron
        super().tearDown()

    def _set_cron_timeout(self, minutes: int):
        """Utility to tweak cron timeout during tests."""
        tools.config["limit_time_real_cron"] = minutes

    def _create_job(self, **vals):
        """Helper to build a bg.job record with sensible defaults."""
        defaults = {
            "name": "Test Job",
            "model": "res.partner",
            "method": "exists",
        }
        defaults.update(vals)
        return self.BgJob.create(defaults)

    def test_create_bg_job(self):
        """Basic test for job creation."""
        job = self._create_job()

        self.assertEqual(job.name, "Test Job")
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.model, "res.partner")
        self.assertEqual(job.method, "exists")

    def test_job_cancel(self):
        """Basic test for job cancellation."""
        job = self._create_job(name="Cancel Test Job")

        job.action_cancel()
        self.assertEqual(job.state, "canceled")

    def test_job_retry(self):
        """Basic test for job retry."""
        job = self._create_job(name="Retry Test Job", state="failed")

        job.action_retry()
        self.assertEqual(job.state, "enqueued")

    def test_job_run_not_enqueued_error(self):
        """Test that only enqueued jobs can be run."""
        job = self._create_job(state="done")

        with self.assertRaises(UserError):
            job.run()

    def test_cron_check_running_jobs(self):
        """Test cron method for checking timed out running jobs."""
        # Create a job that appears to be running for too long
        old_time = fields.Datetime.now() - timedelta(hours=6)
        job = self._create_job(name="Timed Out Job", state="running", start_time=old_time)

        # Run the cron method
        self._set_cron_timeout(300)
        self.BgJob._cron_check_running_jobs()

        # Refresh the job from database
        job = self.BgJob.browse(job.id)
        self.assertEqual(job.state, "failed")

    def test_cron_check_running_jobs_recent(self):
        """Test that recent running jobs are not marked as timed out."""
        # Create a job that started recently
        recent_time = fields.Datetime.now() - timedelta(minutes=30)
        job = self._create_job(name="Recent Job", state="running", start_time=recent_time)

        # Run the cron method
        self._set_cron_timeout(300)
        self.BgJob._cron_check_running_jobs()

        # Refresh the job from database
        job = self.BgJob.browse(job.id)
        self.assertEqual(job.state, "running")  # Should still be running

    def test_job_duration_computation(self):
        """Test that job duration is computed correctly."""
        start_time = fields.Datetime.now()
        end_time = start_time + timedelta(seconds=30)

        job = self._create_job(
            name="Duration Test Job",
            start_time=start_time,
            end_time=end_time,
        )
        self.assertEqual(job.duration, 30.0)

    def test_jobs_are_sorted_by_priority(self):
        """Jobs with lower priority value should be returned first."""
        low_priority = self._create_job(name="Low Priority", priority=20)
        high_priority = self._create_job(name="High Priority", priority=0)

        jobs = self.BgJob.search(
            [("id", "in", [low_priority.id, high_priority.id])],
            order="priority, create_date desc",
        )
        self.assertEqual(jobs[0], high_priority)

    def test_action_open_records_returns_expected_domain(self):
        """The helper action must target the provided record IDs."""
        partner_1 = self.env["res.partner"].create({"name": "Partner 1"})
        partner_2 = self.env["res.partner"].create({"name": "Partner 2"})
        job = self._create_job(
            name="Job with records",
            kwargs_json={"_record_ids": [partner_1.id, partner_2.id]},
        )

        action = job.action_open_records()

        self.assertEqual(action["res_model"], "res.partner")
        self.assertEqual(action["view_mode"], "list,form")
        domain_field, operator, ids = action["domain"][0]
        self.assertEqual(domain_field, "id")
        self.assertEqual(operator, "in")
        self.assertCountEqual(ids, [partner_1.id, partner_2.id])

    def test_run_notifies_only_for_truthy_results(self):
        """Successful job results should trigger a notification."""
        target_job = self._create_job(name="Target Job")
        runner_job = self._create_job(
            name="Runner Job",
            model="bg.job",
            method="dummy_success_method",
            kwargs_json={"_record_ids": [target_job.id]},
        )

        with patch.object(
            type(target_job),
            "dummy_success_method",
            create=True,
            return_value="Done",
        ) as mock_method, patch.object(
            type(runner_job),
            "_notify_user",
        ) as mock_notify, patch.object(
            runner_job.env.cr,
            "commit",
            return_value=None,
        ):
            runner_job.run()

        mock_method.assert_called_once()
        mock_notify.assert_called_once_with("Done")

    def test_run_skip_notification_for_falsy_results(self):
        """Falsy job results must not spam the notification channel."""
        target_job = self._create_job(name="Skip Notify Target")
        runner_job = self._create_job(
            name="Skip Notify Runner",
            model="bg.job",
            method="dummy_false_method",
            kwargs_json={"_record_ids": [target_job.id]},
        )

        with patch.object(
            type(target_job),
            "dummy_false_method",
            create=True,
            return_value=None,
        ) as mock_method, patch.object(
            type(runner_job),
            "_notify_user",
        ) as mock_notify, patch.object(
            runner_job.env.cr,
            "commit",
            return_value=None,
        ):
            runner_job.run()

        mock_method.assert_called_once()
        mock_notify.assert_not_called()
