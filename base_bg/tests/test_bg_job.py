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
            "batch_key": str(uuid4()),
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

    def test_jobs_are_sorted_by_priority(self):
        """Jobs with lower priority value should be returned first."""
        low_priority = self._create_job(name="Low Priority", priority=20)
        high_priority = self._create_job(name="High Priority", priority=0)

        jobs = self.BgJob.search([("id", "in", [low_priority.id, high_priority.id])])
        self.assertEqual(jobs[0], high_priority)

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
        batch_key = jobs[0].batch_key
        self.assertTrue(batch_key)

        sizes = [len(j.kwargs_json.get("_record_ids", [])) for j in jobs]
        self.assertEqual(sizes, [2, 2, 1])

        for i, job in enumerate(jobs):
            self.assertEqual(job.batch_key, batch_key)
            self.assertEqual(job.model, "res.partner")
            self.assertEqual(job.method, "dummy_batch_method")
            if i == 0:
                self.assertEqual(job.state, "enqueued")
            else:
                self.assertEqual(job.state, "waiting")
            if i < len(jobs) - 1:
                self.assertEqual(job.next_job_id, jobs[i + 1])

    def test_fail_first_job_cancels_following_batch_jobs(self):
        """When a job fails permanently, all next jobs in the same batch are canceled."""
        batch_key = str(uuid4())
        # Create three linked jobs in the same batch
        job1 = self._create_job(name="Failing Job", batch_key=batch_key, state="enqueued", max_retries=1)
        job2 = self._create_job(name="Next Job 1", batch_key=batch_key, state="waiting")
        job3 = self._create_job(name="Next Job 2", batch_key=batch_key, state="waiting")
        job1.next_job_id = job2.id
        job2.next_job_id = job3.id

        # Force the job to be considered at its final retry and trigger error handling
        job1.write({"retry_count": job1.max_retries - 1})

        # Call the handler to simulate a permanent failure
        with patch("odoo.addons.base_bg.models.bg_job._logger.error"):
            job1._handle_job_error("Permanent failure")

        # Refresh records from DB
        job1 = self.BgJob.browse(job1.id)
        job2 = self.BgJob.browse(job2.id)
        job3 = self.BgJob.browse(job3.id)

        self.assertEqual(job1.state, "failed")
        self.assertEqual(job2.state, "canceled")
        self.assertEqual(job3.state, "canceled")
        # Canceled jobs must have a cancel_time and an explanatory error_message
        self.assertIsNotNone(job2.cancel_time)
        self.assertIn("Canceled due to previous job failure", job2.error_message)

    def test_bg_enqueue_helper_delegates_to_bg_enqueue_records(self):
        """bg_enqueue helper must delegate to bg_enqueue_records with self as records."""
        job_name = f"Helper Test Job {uuid4().hex}"
        with patch.object(type(self.base_bg_model), "_trigger_crons"), patch.object(
            type(self.base_bg_model), "bg_enqueue_records"
        ) as mock_enqueue_records:
            self.env["base.bg"].bg_enqueue("dummy_method", threshold=5, name=job_name, priority=2)

        mock_enqueue_records.assert_called_once_with(self.env["base.bg"], "dummy_method", 5, name=job_name, priority=2)

    def test_is_serializable_filters_json_safe_values(self):
        """is_serializable must return True for JSON serializable values and False otherwise."""
        base_bg = self.env["base.bg"]
        self.assertTrue(base_bg.is_serializable("string"))
        self.assertTrue(base_bg.is_serializable(123))
        self.assertTrue(base_bg.is_serializable([1, 2, 3]))
        self.assertTrue(base_bg.is_serializable({"key": "value"}))
        self.assertFalse(base_bg.is_serializable(self.env))  # Environment object
        self.assertFalse(base_bg.is_serializable(lambda x: x))  # Function

    def test_get_next_jobs_returns_chained_jobs(self):
        """_get_next_jobs must return all subsequent jobs in the batch chain."""
        job1 = self._create_job(name="Job 1", batch_key="test-batch")
        job2 = self._create_job(name="Job 2", batch_key="test-batch")
        job3 = self._create_job(name="Job 3", batch_key="test-batch")
        job1.next_job_id = job2
        job2.next_job_id = job3

        next_jobs = job1._get_next_jobs()
        self.assertEqual(next_jobs, job2 | job3)

    def test_job_completion_enqueues_next_job(self):
        """When a job completes successfully, the next job in batch must be enqueued."""
        batch_key = str(uuid4())
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        job1 = self._create_job(
            name="First Job",
            batch_key=batch_key,
            state="enqueued",
            kwargs_json={"_record_ids": [partner.id]},
        )
        job2 = self._create_job(
            name="Next Job",
            batch_key=batch_key,
            state="waiting",
        )
        job1.next_job_id = job2

        # Simulate job run completion
        with patch.object(self.env.cr, "commit"):
            job1.run()

        job2.invalidate_recordset()
        self.assertEqual(job2.state, "enqueued")
