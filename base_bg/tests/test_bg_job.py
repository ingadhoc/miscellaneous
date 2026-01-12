##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from odoo import fields, tools
from odoo.addons.base_bg.models.base_bg import BaseBg
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBgJob(TransactionCase):
    def setUp(self):
        """Prepare environment references and keep cron timeout to restore later."""
        super(TestBgJob, self).setUp()
        self.BgJob = self.env["bg.job"]
        self.base_bg_model = self.env["base.bg"]
        self._limit_time_real_cron = tools.config.get("limit_time_real_cron", 120)

    def tearDown(self):
        """Restore original cron timeout and teardown TransactionCase."""
        tools.config["limit_time_real_cron"] = self._limit_time_real_cron
        super().tearDown()

    def _set_cron_timeout(self, minutes: int):
        """Utility to tweak cron timeout (expressed in minutes)."""
        tools.config["limit_time_real_cron"] = int(minutes * 60)

    def _create_job(self, **vals):
        """Helper to build a bg.job record with sensible defaults."""
        defaults = {
            "name": "Test Job",
            "model": "res.partner",
            "method": "exists",
            "batch_id": str(uuid4()),
        }
        defaults.update(vals)
        return self.BgJob.create(defaults)

    def _job_by_name(self, name):
        """Locate a bg.job record by its name."""
        return self.BgJob.search([("name", "=", name)], limit=1)

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
        job = self._create_job(name="Timed Out Job", state="running", start_time=old_time, max_retries=1)

        # Run the cron method
        self._set_cron_timeout(300)
        with patch("odoo.addons.base_bg.models.bg_job._logger.error"):
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

    def test_bg_enqueue_applies_custom_priority(self):
        """bg_enqueue must propagate the provided priority into bg.job."""
        job_name = f"Priority Test Job {uuid4().hex}"
        partners = self.env["res.partner"].create([{"name": "Test Partner 1"}])
        with patch.object(BaseBg, "_trigger_crons"):
            self.env["base.bg"].bg_enqueue_records(
                partners,
                "dummy_priority_method",
                name=job_name,
                priority=3,
            )

        job = self._job_by_name(job_name)
        self.assertTrue(job, "The priority test job should exist")
        self.assertEqual(job.priority, 3)

    def test_bg_enqueue_filters_unserializable_context_entries(self):
        """Only JSON-safe context keys should be stored in bg.job."""
        job_name = f"Context Test Job {uuid4().hex}"
        partners = self.env["res.partner"].create([{"name": "Test Partner"}])
        with patch.object(BaseBg, "_trigger_crons"):
            self.env["base.bg"].with_context(
                serializable_flag="ok",
                unserializable_env=self.env,
            ).bg_enqueue_records(partners, "dummy_context_method", name=job_name)

        job = self._job_by_name(job_name)
        self.assertTrue(job, "The context test job should exist")
        self.assertEqual(job.context_json, {"serializable_flag": "ok"})

    def test_get_next_job_returns_highest_priority_enqueued_job(self):
        """_get_next_job should return the highest priority enqueued job, skipping others."""
        self._create_job(name="Running Job", state="running", priority=1, batch_id=str(uuid4()))
        self._create_job(name="Low Priority Job", priority=20, batch_id=str(uuid4()))
        high_priority = self._create_job(name="High Priority Job", priority=5, batch_id=str(uuid4()))

        next_job = self.BgJob._get_next_job()

        self.assertEqual(next_job, high_priority)

    def test_cron_run_enqueued_jobs_executes_one_job_and_retriggers(self):
        """_cron_run_enqueued_jobs executes one job and triggers cron if more pending."""
        batch_id = str(uuid4())
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        job1 = self._create_job(
            name="Job 1",
            priority=1,
            batch_id=batch_id,
            kwargs_json={"_record_ids": [partner.id]},
        )
        job2 = self._create_job(
            name="Job 2",
            priority=2,
            batch_id=batch_id,
            kwargs_json={"_record_ids": [partner.id]},
        )

        with patch.object(self.env.cr, "commit", return_value=None), patch.object(
            type(self.base_bg_model), "_trigger_crons"
        ) as mock_trigger:
            self.BgJob._cron_run_enqueued_jobs()

        job1.invalidate_recordset()
        job2.invalidate_recordset()
        self.assertEqual(job1.state, "done")
        self.assertEqual(job2.state, "enqueued")
        mock_trigger.assert_called_once()

    def test_cron_run_enqueued_jobs_no_retrigger_when_last_job(self):
        """_cron_run_enqueued_jobs should not trigger crons after processing last job."""
        self._create_job(name="Only Job", priority=1)

        with patch.object(self.env.cr, "commit", return_value=None), patch.object(
            type(self.base_bg_model), "_trigger_crons"
        ) as mock_trigger:
            self.BgJob._cron_run_enqueued_jobs()

        mock_trigger.assert_not_called()

    def test_jobs_linking_and_states_after_enqueue(self):
        """Ensure bg_enqueue links jobs via next_job_id and sets states correctly."""
        partners = self.env["res.partner"].create([{"name": f"Partner {i}"} for i in range(3)])
        job_name = f"Linked Batch Job {uuid4().hex}"
        with patch.object(BaseBg, "_trigger_crons"):
            _, jobs = self.env["base.bg"].bg_enqueue_records(partners, "dummy_batch_method", threshold=1, name=job_name)

        self.assertEqual(len(jobs), 3)
        # first must be enqueued and point to the next; others waiting
        self.assertEqual(jobs[0].state, "enqueued")
        self.assertEqual(jobs[0].next_job_id, jobs[1])
        self.assertEqual(jobs[1].state, "waiting")
        self.assertEqual(jobs[1].next_job_id, jobs[2])
        self.assertEqual(jobs[2].state, "waiting")

    def test_bg_enqueue_records_creates_job_when_no_records(self):
        """Calling bg_enqueue_records with no records must still create a job."""
        job_name = f"No Records Job {uuid4().hex}"
        with patch.object(BaseBg, "_trigger_crons"):
            _, job = self.env["base.bg"].bg_enqueue_records(self.env["res.partner"], "dummy_method", name=job_name)

        self.assertTrue(job, "A job should have been created even with no records")
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.kwargs_json.get("_record_ids"), [])

    def test_bg_enqueue_records_splits_by_threshold(self):
        """bg_enqueue_records must split partner records into multiple jobs by threshold."""
        partners = self.env["res.partner"].create([{"name": f"Partner {i}"} for i in range(5)])
        threshold = 2
        job_name = f"Batch Partners {uuid4().hex}"

        with patch.object(BaseBg, "_trigger_crons"):
            _, jobs = self.env["base.bg"].bg_enqueue_records(
                partners, "dummy_batch_method", threshold=threshold, name=job_name
            )

        # Expect 3 jobs: 2,2,1
        self.assertEqual(len(jobs), 3)
        batch_id = jobs[0].batch_id
        self.assertTrue(batch_id)

        sizes = [len(j.kwargs_json.get("_record_ids", [])) for j in jobs]
        self.assertEqual(sizes, [2, 2, 1])

        for i, job in enumerate(jobs):
            self.assertEqual(job.batch_id, batch_id)
            self.assertEqual(job.model, "res.partner")
            self.assertEqual(job.method, "dummy_batch_method")
            if i == 0:
                self.assertEqual(job.state, "enqueued")
            else:
                self.assertEqual(job.state, "waiting")
            if i < len(jobs) - 1:
                self.assertEqual(job.next_job_id, jobs[i + 1])

    def test_get_next_job_respects_batch_order(self):
        """_get_next_job should return batch jobs in sequential order."""
        batch_id = str(uuid4())
        # Create a chain where only the first is enqueued; others are waiting and linked
        job1 = self._create_job(name="Batch Job 1", batch_id=batch_id, state="enqueued", priority=10)
        job2 = self._create_job(name="Batch Job 2", batch_id=batch_id, state="waiting", priority=10)
        job3 = self._create_job(name="Batch Job 3", batch_id=batch_id, state="waiting", priority=10)
        job1.next_job_id = job2.id
        job2.next_job_id = job3.id

        # First call should return job1
        next_job = self.BgJob._get_next_job()
        self.assertEqual(next_job, job1, "Should return first job in batch")

        # Simulate a successful run of job1 to enqueue job2
        # Patch a dummy method on bg.job to avoid side effects
        with patch.object(type(job1), "dummy_run", create=True, return_value=None), patch.object(
            job1.env.cr, "commit", return_value=None
        ):
            job1.method = "dummy_run"
            job1.model = "bg.job"
            job1.run()

        # Now _get_next_job should return job2
        next_job = self.BgJob._get_next_job()
        self.assertEqual(next_job, job2, "Should return second job after first ran successfully")
