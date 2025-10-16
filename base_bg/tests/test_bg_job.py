from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBgJob(TransactionCase):
    def setUp(self):
        super(TestBgJob, self).setUp()
        self.BgJob = self.env["bg.job"]

    def test_create_bg_job(self):
        """Basic test for job creation."""
        job = self.BgJob.create(
            {
                "name": "Test Job",
                "model": "res.partner",
                "method": "exists",
            }
        )

        self.assertEqual(job.name, "Test Job")
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.model, "res.partner")
        self.assertEqual(job.method, "exists")

    def test_job_cancel(self):
        """Basic test for job cancellation."""
        job = self.BgJob.create(
            {
                "name": "Cancel Test Job",
                "model": "res.partner",
                "method": "exists",
            }
        )

        job.action_cancel()
        self.assertEqual(job.state, "canceled")

    def test_job_retry(self):
        """Basic test for job retry."""
        job = self.BgJob.create(
            {
                "name": "Retry Test Job",
                "model": "res.partner",
                "method": "exists",
                "state": "failed",
            }
        )

        job.action_retry()
        self.assertEqual(job.state, "enqueued")

    def test_job_run_not_enqueued_error(self):
        """Test that only enqueued jobs can be run."""
        job = self.BgJob.create(
            {
                "name": "Test Job",
                "model": "res.partner",
                "method": "exists",
                "state": "done",
            }
        )

        with self.assertRaises(UserError):
            job.run()

    def test_cron_check_running_jobs(self):
        """Test cron method for checking timed out running jobs."""
        # Create a job that appears to be running for too long
        old_time = fields.Datetime.now() - timedelta(hours=6)
        job = self.BgJob.create(
            {
                "name": "Timed Out Job",
                "model": "res.partner",
                "method": "exists",
                "state": "running",
                "start_time": old_time,
            }
        )

        # Run the cron method
        self.BgJob._cron_check_running_jobs(minutes=300)  # 5 hours

        # Refresh the job from database
        job = self.BgJob.browse(job.id)
        self.assertEqual(job.state, "failed")

    def test_cron_check_running_jobs_recent(self):
        """Test that recent running jobs are not marked as timed out."""
        # Create a job that started recently
        recent_time = fields.Datetime.now() - timedelta(minutes=30)
        job = self.BgJob.create(
            {
                "name": "Recent Job",
                "model": "res.partner",
                "method": "exists",
                "state": "running",
                "start_time": recent_time,
            }
        )

        # Run the cron method
        self.BgJob._cron_check_running_jobs(minutes=300)  # 5 hours

        # Refresh the job from database
        job = self.BgJob.browse(job.id)
        self.assertEqual(job.state, "running")  # Should still be running

    def test_job_duration_computation(self):
        """Test that job duration is computed correctly."""
        start_time = fields.Datetime.now()
        end_time = start_time + timedelta(seconds=30)

        job = self.BgJob.create(
            {
                "name": "Duration Test Job",
                "model": "res.partner",
                "method": "exists",
                "start_time": start_time,
                "end_time": end_time,
            }
        )

        self.assertEqual(job.duration, 30.0)
