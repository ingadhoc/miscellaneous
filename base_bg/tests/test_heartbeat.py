import time
from datetime import timedelta
from unittest.mock import patch

from odoo import fields, tools
from odoo.tests.common import TransactionCase


class TestHeartbeat(TransactionCase):
    def setUp(self):
        super().setUp()
        self.BgJob = self.env["bg.job"]

    def _set_cron_timeout(self, seconds: int):
        """Set cron timeout in seconds for testing"""
        tools.config["limit_time_real_cron"] = seconds

    def test_job_with_heartbeat_does_not_timeout(self):
        """Test that jobs updating heartbeat don't timeout even if they exceed cron timeout"""
        self._set_cron_timeout(60)

        # Create a running job with old start_time but recent heartbeat
        old_start = fields.Datetime.now() - timedelta(seconds=120)
        recent_heartbeat = fields.Datetime.now() - timedelta(seconds=30)

        job = self.BgJob.create(
            {
                "name": "Long Job with Heartbeat",
                "model": "res.partner",
                "method": "exists",
                "state": "running",
                "start_time": old_start,
                "last_heartbeat": recent_heartbeat,
            }
        )

        # Run monitor
        self.BgJob._cron_check_running_jobs()

        # Job should still be running because heartbeat is recent
        job = self.BgJob.browse(job.id)
        self.assertEqual(job.state, "running", "Job with recent heartbeat should not timeout")

    def test_job_without_heartbeat_times_out(self):
        """Test that jobs without heartbeat updates DO timeout"""
        self._set_cron_timeout(60)

        # Create a running job with old start_time AND old heartbeat
        old_time = fields.Datetime.now() - timedelta(seconds=120)

        job = self.BgJob.create(
            {
                "name": "Long Job without Heartbeat",
                "model": "res.partner",
                "method": "exists",
                "state": "running",
                "start_time": old_time,
                "last_heartbeat": old_time,
            }
        )

        # Run monitor
        self.BgJob._cron_check_running_jobs()

        # Job should be marked as failed
        job = self.BgJob.browse(job.id)
        self.assertEqual(job.state, "failed", "Job without heartbeat should timeout")
        self.assertIn("timed out", job.error_message.lower())

    def test_update_heartbeat_method(self):
        """Test that update_heartbeat updates the timestamp correctly"""
        job = self.BgJob.create(
            {
                "name": "Test Heartbeat Update",
                "model": "res.partner",
                "method": "exists",
                "state": "running",
                "start_time": fields.Datetime.now(),
                "last_heartbeat": fields.Datetime.now() - timedelta(seconds=60),
            }
        )

        old_heartbeat = job.last_heartbeat
        time.sleep(1)  # Wait a bit to ensure timestamp changes

        # Mock commit to avoid test failure
        with patch.object(self.env.cr, "commit"):
            job.update_heartbeat()

        self.assertGreater(job.last_heartbeat, old_heartbeat, "Heartbeat should be updated to a newer timestamp")
