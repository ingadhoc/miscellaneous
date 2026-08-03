##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import psycopg2
from odoo import fields, tools
from odoo.addons.base_bg.models.base_bg import BaseBg
from odoo.addons.base_bg.models.bg_job import MAX_ACQUIRE_RETRIES
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
        # Create a chain of jobs
        job1 = self._create_job(name="Cancel Test Job 1")
        job2 = self._create_job(name="Cancel Test Job 2", state="waiting")
        job3 = self._create_job(name="Cancel Test Job 3", state="waiting")
        job1.next_job_id = job2
        job2.next_job_id = job3

        # Cancel the first job
        job1.action_cancel()

        # Refresh from DB
        job1 = self.BgJob.browse(job1.id)
        job2 = self.BgJob.browse(job2.id)
        job3 = self.BgJob.browse(job3.id)

        # All jobs in the chain should be canceled
        self.assertEqual(job1.state, "canceled")
        self.assertEqual(job2.state, "canceled")
        self.assertEqual(job3.state, "canceled")
        # Canceled jobs should have cancel_time set
        self.assertIsNotNone(job1.cancel_time)
        self.assertIsNotNone(job2.cancel_time)
        self.assertIsNotNone(job3.cancel_time)

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
            state="running",
            kwargs_json={"_record_ids": [target_job.id]},
        )

        with (
            patch.object(
                type(target_job),
                "dummy_success_method",
                create=True,
                return_value="Done",
            ) as mock_method,
            patch.object(
                type(runner_job),
                "_notify_user",
            ) as mock_notify,
            patch.object(
                runner_job.env.cr,
                "commit",
                return_value=None,
            ),
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
            state="running",
            kwargs_json={"_record_ids": [target_job.id]},
        )

        with (
            patch.object(
                type(target_job),
                "dummy_false_method",
                create=True,
                return_value=None,
            ) as mock_method,
            patch.object(
                type(runner_job),
                "_notify_user",
            ) as mock_notify,
            patch.object(
                runner_job.env.cr,
                "commit",
                return_value=None,
            ),
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

    def test_bg_enqueue_helper_delegates_to_bg_enqueue_records(self):
        """bg_enqueue helper must delegate to bg_enqueue_records with self as records."""
        job_name = f"Helper Test Job {uuid4().hex}"
        with (
            patch.object(type(self.base_bg_model), "_trigger_crons"),
            patch.object(type(self.base_bg_model), "bg_enqueue_records") as mock_enqueue_records,
        ):
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
            state="running",
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

    def test_check_serializable(self):
        """check_serializable must raise ValueError for unserializable objects."""
        base_bg = self.env["base.bg"]
        # env is not serializable
        dict_data = {
            "serializable": "ok",
            "unserializable": self.env,
        }
        list_data = ["ok", self.env, 123]
        function_data = lambda x: x
        with self.assertRaises(ValueError):
            base_bg.check_serializable(dict_data)
        with self.assertRaises(ValueError):
            base_bg.check_serializable(list_data)
        with self.assertRaises(ValueError):
            base_bg.check_serializable(function_data)

    def test_get_next_job_returns_enqueued_job(self):
        """_get_next_job should return an available enqueued job."""
        job = self._create_job(name="Test Next Job", state="enqueued")
        next_job = self.BgJob._get_next_job()
        self.assertEqual(next_job, job)

    def test_get_next_job_returns_empty_when_no_jobs(self):
        """_get_next_job should return an empty recordset when no enqueued jobs exist."""
        # Ensure no enqueued jobs
        self.BgJob.search([("state", "=", "enqueued")]).unlink()
        next_job = self.BgJob._get_next_job()
        self.assertEqual(next_job, self.env["bg.job"])

    def test_cron_run_enqueued_jobs_executes_job(self):
        """_cron_run_enqueued_jobs should execute one enqueued job."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        job = self._create_job(
            name="Cron Run Test Job",
            model="res.partner",
            method="exists",
            kwargs_json={"_record_ids": [partner.id]},
            state="enqueued",
        )
        with patch.object(type(job), "run") as mock_run:
            self.BgJob._cron_run_enqueued_jobs()
            mock_run.assert_called_once()

    def test_enqueue_registers_trigger_crons_as_postcommit(self):
        """_trigger_crons must be registered as a postcommit callback, not called via an
        eager cr.commit(), so that the caller's transaction remains atomic.

        The postcommit hook fires after the caller's own commit, at which point both the
        bg.job row and the caller's data are visible to the cron worker — no race condition
        and no atomicity violation.
        """
        partners = self.env["res.partner"].create([{"name": "P1"}, {"name": "P2"}])
        registered = []

        original_add = self.env.cr.postcommit.add

        def capture_add(func):
            registered.append(func)
            return original_add(func)

        with (
            patch.object(type(self.env.cr.postcommit), "add", side_effect=capture_add),
            patch.object(BaseBg, "_trigger_crons"),
        ):
            self.env["base.bg"].bg_enqueue_records(partners, "dummy_ordering_method", threshold=1)

        self.assertTrue(
            registered,
            "bg_enqueue_records must register _trigger_crons via cr.postcommit.add, not call it eagerly",
        )

    def test_enqueue_does_not_commit_eagerly(self):
        """bg_enqueue_records must not call cr.commit() directly — the caller owns the
        transaction boundary. An eager commit would persist caller's in-flight changes
        even if the caller later raises, breaking atomicity."""
        partners = self.env["res.partner"].create([{"name": f"P{i}"} for i in range(5)])

        with patch.object(self.env.cr, "commit") as mock_commit, patch.object(BaseBg, "_trigger_crons"):
            self.env["base.bg"].bg_enqueue_records(partners, "dummy_batch_commit_method", threshold=1)

        mock_commit.assert_not_called()

    def test_cron_run_enqueued_jobs_triggers_cron_if_more_jobs(self):
        """_cron_run_enqueued_jobs should trigger crons if more jobs remain."""
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        job1 = self._create_job(
            name="Cron Trigger Test Job 1",
            model="res.partner",
            method="exists",
            kwargs_json={"_record_ids": [partner.id]},
            state="enqueued",
        )
        self._create_job(
            name="Cron Trigger Test Job 2",
            model="res.partner",
            method="exists",
            kwargs_json={"_record_ids": [partner.id]},
            state="enqueued",
        )
        with patch.object(type(job1), "run"), patch.object(type(self.env["base.bg"]), "_trigger_crons") as mock_trigger:
            self.BgJob._cron_run_enqueued_jobs()
            mock_trigger.assert_called_once()

    def test_cron_run_retries_on_serialization_failure(self):
        """A SerializationFailure while acquiring a job must be retried in-process,
        not surrendered on the first conflict (which caused the trigger storm)."""
        partner = self.env["res.partner"].create({"name": "Retry Partner"})
        job = self._create_job(
            name="Retry Race Job",
            model="res.partner",
            method="exists",
            kwargs_json={"_record_ids": [partner.id]},
            state="enqueued",
        )
        # First acquire loses the race; the retry succeeds and returns the job.
        outcomes = [psycopg2.errors.SerializationFailure(), job]

        def fake_get_next_job():
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with (
            patch.object(type(self.BgJob), "_get_next_job", side_effect=fake_get_next_job) as mock_get,
            patch.object(self.env.cr, "rollback"),
            patch.object(type(job), "run") as mock_run,
        ):
            self.BgJob._cron_run_enqueued_jobs()

        self.assertEqual(mock_get.call_count, 2, "must retry once after the SerializationFailure")
        mock_run.assert_called_once()

    def test_cron_run_surrenders_after_max_retries(self):
        """After MAX_ACQUIRE_RETRIES consecutive SerializationFailures, the cron
        reschedules and returns without running a job."""
        with (
            patch.object(
                type(self.BgJob),
                "_get_next_job",
                side_effect=psycopg2.errors.SerializationFailure(),
            ) as mock_get,
            patch.object(self.env.cr, "rollback"),
            patch.object(type(self.env["base.bg"]), "_trigger_crons") as mock_trigger,
            patch("odoo.addons.base_bg.models.bg_job._logger.warning") as mock_warning,
        ):
            result = self.BgJob._cron_run_enqueued_jobs()

        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, MAX_ACQUIRE_RETRIES)
        mock_trigger.assert_called_once()
        mock_warning.assert_called_once()

    def test_cron_run_reraises_unexpected_error(self):
        """An error other than SerializationFailure must not be retried: the cron
        rolls back the aborted transaction and propagates it (no silent swallow)."""
        with (
            patch.object(
                type(self.BgJob),
                "_get_next_job",
                side_effect=ValueError("boom"),
            ) as mock_get,
            patch.object(self.env.cr, "rollback") as mock_rollback,
        ):
            with self.assertRaises(ValueError):
                self.BgJob._cron_run_enqueued_jobs()

        # Not retried, and the transaction is rolled back before propagating.
        self.assertEqual(mock_get.call_count, 1)
        mock_rollback.assert_called_once()

    # --- Serialization backoff, eligibility and concurrency cap -------------

    def test_is_transient_error_detects_serialization(self):
        """Serialization failures (SQLSTATE 40001) must be classified as transient."""
        job = self._create_job()

        class _FakeSerializationError(psycopg2.Error):
            pgcode = "40001"

        # By message (fallback path) and by pgcode on a psycopg2 error
        self.assertTrue(job._is_transient_error("could not serialize access due to concurrent update"))
        self.assertTrue(job._is_transient_error(_FakeSerializationError()))
        # Unrelated errors are not transient
        self.assertFalse(job._is_transient_error("Some other failure"))
        self.assertFalse(job._is_transient_error(ValueError("boom")))

    def test_transient_error_backs_off_and_reenqueues(self):
        """A serialization failure re-enqueues with a future backoff gate instead of failing."""
        job = self._create_job(name="Transient Job", state="running", max_retries=3)
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"):
            job._handle_job_error("could not serialize access due to concurrent update")

        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.retry_count, 1)
        self.assertTrue(job.next_retry_at, "A backoff gate must be set for transient errors")
        self.assertGreater(job.next_retry_at, fields.Datetime.now())

    def test_transient_error_does_not_consume_normal_retry_budget(self):
        """Serialization retries use the larger serialization budget, not max_retries."""
        # max_retries is 3, but a transient error past it must still keep retrying.
        job = self._create_job(name="Persistent Transient", state="running", max_retries=3, retry_count=5)
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"):
            job._handle_job_error("could not serialize access due to concurrent update")

        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")  # not failed despite retry_count > max_retries
        self.assertEqual(job.retry_count, 6)

    def test_transient_error_fails_after_serialization_cap(self):
        """Once the serialization retry cap is reached, the job fails permanently."""
        self.env["ir.config_parameter"].sudo().set_param("base_bg.serialization_max_retries", "3")
        job = self._create_job(name="Exhausted Transient", state="running", retry_count=2)
        with patch("odoo.addons.base_bg.models.bg_job._logger.error"):
            job._handle_job_error("could not serialize access due to concurrent update")

        job.invalidate_recordset()
        self.assertEqual(job.state, "failed")

    def test_non_transient_error_keeps_immediate_retry(self):
        """Non-serialization errors keep the original retry-then-fail behavior, no backoff gate."""
        job = self._create_job(name="Real Error Job", state="running", max_retries=2)
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"):
            job._handle_job_error("Some real failure")

        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.retry_count, 1)
        self.assertFalse(job.next_retry_at, "Non-transient retries must not set a backoff gate")

    def test_get_next_job_skips_jobs_in_backoff(self):
        """Jobs whose backoff window is still in the future are not picked up."""
        self.BgJob.search([("state", "=", "enqueued")]).write({"state": "canceled"})
        future = fields.Datetime.now() + timedelta(minutes=10)
        self._create_job(name="Backing Off", state="enqueued", next_retry_at=future)
        self.assertEqual(self.BgJob._get_next_job(), self.env["bg.job"])

        eligible = self._create_job(name="Ready", state="enqueued")
        self.assertEqual(self.BgJob._get_next_job(), eligible)

    def test_get_next_job_respects_concurrency_cap(self):
        """With the cap set and already reached, no new job is picked."""
        self.BgJob.search([("state", "in", ["enqueued", "running"])]).write({"state": "canceled"})
        self.env["ir.config_parameter"].sudo().set_param("base_bg.max_concurrent_jobs", "1")
        self._create_job(name="Already Running", state="running", start_time=fields.Datetime.now())
        self._create_job(name="Waiting For Slot", state="enqueued")

        self.assertEqual(self.BgJob._get_next_job(), self.env["bg.job"])

    def test_concurrency_cap_disabled_by_default(self):
        """With the default parameter (0) the cap is off and jobs run normally."""
        self.BgJob.search([("state", "in", ["enqueued", "running"])]).write({"state": "canceled"})
        self._create_job(name="Running A", state="running", start_time=fields.Datetime.now())
        job = self._create_job(name="Should Still Run", state="enqueued")

        self.assertEqual(self.BgJob._get_next_job(), job)

    def test_finish_does_not_trigger_cron(self):
        """finish() must not hammer the cron on every completed job."""
        job = self._create_job(name="Finish No Trigger", state="running")
        with patch.object(type(self.env["base.bg"]), "_trigger_crons") as mock_trigger:
            job.finish()

        job.invalidate_recordset()
        self.assertEqual(job.state, "done")
        mock_trigger.assert_not_called()
