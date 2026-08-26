##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import psycopg2
from markupsafe import Markup
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
        self._limit_time_real = tools.config.get("limit_time_real")
        self._workers = tools.config.get("workers")

    def tearDown(self):
        """Restore original time limits / server mode and teardown TransactionCase."""
        tools.config["limit_time_real_cron"] = self._limit_time_real_cron
        tools.config["limit_time_real"] = self._limit_time_real
        tools.config["workers"] = self._workers
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

    def test_fail_notifies_when_records_were_deleted(self):
        """fail() must not raise when the job outlived the records it points to."""
        partner = self.env["res.partner"].create({"name": "Gone"})
        job = self._create_job(name="Orphan Job", state="running", kwargs_json={"_record_ids": [partner.id]})
        partner.unlink()  # linking it in the notification would read display_name and raise

        job.fail("boom")

        self.assertEqual(job.state, "failed")
        self.assertEqual(job.error_message, "boom")

    def test_fail_notification_escapes_user_data(self):
        """HTML in the job name or error message must reach the DM inert, not injected."""
        job = self._create_job(name="<img src=x onerror=alert(1)>", state="running")

        with patch.object(type(self.BgJob), "_notify_user") as mock_notify:
            job.fail("boom <MissingRecord res.partner>")

        message = mock_notify.call_args[0][0]
        self.assertIsInstance(message, Markup)
        self.assertNotIn("<img", str(message))
        self.assertIn("&lt;MissingRecord res.partner&gt;", str(message))
        # the job link itself stays clickable
        self.assertIn("data-oe-id", str(message))

    def test_notify_user_escapes_plain_strings(self):
        """A plain-string result is escaped; a Markup result keeps its HTML."""
        job = self._create_job()
        channel = (
            self.env["discuss.channel"]
            .with_user(job.create_uid)
            .sudo()
            ._get_or_create_chat([job.create_uid.partner_id.id])
        )

        job._notify_user("plain <b>bold</b>")
        plain_body = str(channel.message_ids[0].body)
        self.assertNotIn("<b>", plain_body)
        self.assertIn("&lt;b&gt;", plain_body)

        job._notify_user(Markup("<b>bold</b>"))
        markup_body = str(channel.message_ids[0].body)
        self.assertIn("<b>bold</b>", markup_body)

    def _create_timed_out_job(self, name, **vals):
        """Build a running job whose start_time is already past any cron timeout."""
        old_time = fields.Datetime.now() - timedelta(hours=6)
        return self._create_job(name=name, state="running", start_time=old_time, max_retries=1, **vals)

    def test_cron_check_running_jobs_notifies_once_on_permanent_timeout(self):
        """A permanently timed-out job must DM its creator once, not twice."""
        job = self._create_timed_out_job("Timed Out Once")

        self._set_cron_timeout(300)
        with patch.object(type(self.BgJob), "_notify_user") as mock_notify, tools.mute_logger(
            "odoo.addons.base_bg.models.bg_job"
        ):
            self.BgJob._cron_check_running_jobs()

        self.assertEqual(job.state, "failed")
        mock_notify.assert_called_once()
        # the single message keeps a clickable reference to the job
        message = mock_notify.call_args[0][0]
        self.assertIn("Timed Out Once", message)
        self.assertIn("data-oe-id", message)

    def test_cron_check_running_jobs_skips_poisoned_job(self):
        """A job that raises while being timed out must not abort the reaper for the rest."""
        poisoned = self._create_timed_out_job("Poisoned Job")
        chained = self._create_job(name="Chained Job", batch_key=poisoned.batch_key, state="waiting")
        poisoned.next_job_id = chained.id
        healthy = self._create_timed_out_job("Healthy Job")
        base_fail = type(self.BgJob).fail

        def poisoned_fail(job_self, error_message, notify=True):
            """Stand in for a model override of fail() that raises (the real-world poison)."""
            if job_self.name == "Poisoned Job":
                raise ValueError("boom while failing the job")
            return base_fail(job_self, error_message, notify=notify)

        self._set_cron_timeout(300)
        with patch.object(type(self.BgJob), "fail", poisoned_fail), tools.mute_logger(
            "odoo.addons.base_bg.models.bg_job"
        ):
            self.BgJob._cron_check_running_jobs()

        self.assertEqual(poisoned.state, "failed", "the poisoned job is bare-failed instead of poisoning every run")
        self.assertEqual(chained.state, "canceled", "its batch is cancelled, as on any other permanent failure")
        self.assertEqual(healthy.state, "failed", "the remaining jobs are still timed out")

    def test_cron_check_running_jobs_defers_transient_error(self):
        """A transient PG error is not a poisoned job: the job is left for the next run."""
        job = self._create_timed_out_job("Contended Job")

        self._set_cron_timeout(300)
        with patch.object(
            type(self.BgJob), "_handle_job_error", side_effect=self._serialization_error()
        ), tools.mute_logger("odoo.addons.base_bg.models.bg_job"):
            self.BgJob._cron_check_running_jobs()

        self.assertEqual(job.state, "running")

    def test_run_cancels_orphaned_job(self):
        """run() cancels a job whose records were all deleted, along with the rest of its batch."""
        partner = self.env["res.partner"].create({"name": "Gone"})
        job = self._create_job(name="Orphan Run Job", state="running", kwargs_json={"_record_ids": [partner.id]})
        chained = self._create_job(name="Chained After Orphan", batch_key=job.batch_key, state="waiting")
        job.next_job_id = chained.id
        partner.unlink()

        with patch.object(type(self.BgJob), "_notify_user") as mock_notify:
            job.run()

        self.assertEqual(job.state, "canceled", "an orphan job is canceled, not failed")
        self.assertEqual(chained.state, "canceled")
        mock_notify.assert_not_called()

    def test_run_with_partially_deleted_records_is_not_orphaned(self):
        """One surviving record is enough: the job is not an orphan and runs normally."""
        keep = self.env["res.partner"].create({"name": "Keep"})
        gone = self.env["res.partner"].create({"name": "Gone"})
        job = self._create_job(state="running", kwargs_json={"_record_ids": [keep.id, gone.id]})
        gone.unlink()

        with patch.object(self.env.cr, "commit"), patch.object(type(self.BgJob), "_notify_user"):
            job.run()

        self.assertEqual(job.state, "done")

    def test_run_with_no_records_is_not_orphaned(self):
        """A job that points to no records at all (model-level method) runs normally."""
        job = self._create_job(state="running", kwargs_json={"_record_ids": []})

        with patch.object(self.env.cr, "commit"):
            job.run()

        self.assertEqual(job.state, "done")

    def test_cron_check_running_jobs_cancels_orphaned_job(self):
        """The reaper cancels a timed-out job whose records are gone, and still times out the rest."""
        partner = self.env["res.partner"].create({"name": "Gone"})
        orphan = self._create_timed_out_job("Orphan Timed Out", kwargs_json={"_record_ids": [partner.id]})
        healthy = self._create_timed_out_job("Healthy Timed Out")
        partner.unlink()

        self._set_cron_timeout(300)
        with patch.object(type(self.BgJob), "_notify_user"), tools.mute_logger("odoo.addons.base_bg.models.bg_job"):
            self.BgJob._cron_check_running_jobs()

        self.assertEqual(orphan.state, "canceled", "an orphan job is canceled, not failed")
        self.assertEqual(healthy.state, "failed")

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

    def test_cron_check_running_jobs_default_config_falls_back_to_limit_time_real(self):
        """-1 (the core default) must inherit --limit-time-real, not reap every running job."""
        recent = self._create_job(
            name="Recent Under Fallback",
            state="running",
            start_time=fields.Datetime.now() - timedelta(minutes=30),
        )
        stale = self._create_timed_out_job("Stale Under Fallback")
        tools.config["limit_time_real_cron"] = -1
        tools.config["limit_time_real"] = 3600
        with patch.object(type(self.BgJob), "_notify_user"), tools.mute_logger("odoo.addons.base_bg.models.bg_job"):
            self.BgJob._cron_check_running_jobs()
        self.assertEqual(recent.state, "running")
        self.assertEqual(stale.state, "failed")

    def test_cron_check_running_jobs_without_time_limit_reaps_nothing(self):
        """In prefork, 0 disables the cron time limit: the reaper must leave running jobs alone."""
        stale = self._create_timed_out_job("Stale Without Limit")
        tools.config["workers"] = 4
        tools.config["limit_time_real_cron"] = 0
        self.BgJob._cron_check_running_jobs()
        self.assertEqual(stale.state, "running")

        # -1 falling back to a limit_time_real of 0 disables it just the same
        tools.config["limit_time_real_cron"] = -1
        tools.config["limit_time_real"] = 0
        self.BgJob._cron_check_running_jobs()
        self.assertEqual(stale.state, "running")

    def test_cron_check_running_jobs_threaded_zero_falls_back_to_limit_time_real(self):
        """In threaded mode 0 is not "no limit": the core falls back to --limit-time-real."""
        stale = self._create_timed_out_job("Stale Threaded Zero")
        tools.config["workers"] = 0
        tools.config["limit_time_real_cron"] = 0
        tools.config["limit_time_real"] = 3600
        with patch.object(type(self.BgJob), "_notify_user"), tools.mute_logger("odoo.addons.base_bg.models.bg_job"):
            self.BgJob._cron_check_running_jobs()
        self.assertEqual(stale.state, "failed")

    def test_cron_check_running_jobs_without_time_limit_still_cancels_orphans(self):
        """No time limit must not turn off the orphan sweep: stuck orphans block their batch."""
        partner = self.env["res.partner"].create({"name": "Gone"})
        orphan = self._create_timed_out_job("Orphan Without Limit", kwargs_json={"_record_ids": [partner.id]})
        chained = self._create_job(name="Chained After Orphan", batch_key=orphan.batch_key, state="waiting")
        orphan.next_job_id = chained.id
        partner.unlink()
        tools.config["workers"] = 4
        tools.config["limit_time_real_cron"] = 0

        self.BgJob._cron_check_running_jobs()

        self.assertEqual(orphan.state, "canceled", "an orphan job is canceled even with no time limit")
        self.assertEqual(chained.state, "canceled")

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

    # --- Serialization backoff, eligibility and runner memory cleanup -------

    def _serialization_error(self):
        """Build a real psycopg2 serialization failure (SQLSTATE 40001)."""
        return psycopg2.errors.SerializationFailure("could not serialize access due to concurrent update")

    def _set_param(self, key, value):
        """Set a system parameter and restore its prior state on cleanup.

        ir.config_parameter is cached in a process-global ormcache that survives
        the TransactionCase rollback, so tests must undo their own set_param.
        """
        icp = self.env["ir.config_parameter"].sudo()
        original = icp.get_param(key, False)

        def _restore():
            if original is False:
                param = icp.search([("key", "=", key)])
                if param:
                    param.unlink()
            else:
                icp.set_param(key, original)

        self.addCleanup(_restore)
        icp.set_param(key, value)

    def test_is_transient_error_detects_serialization(self):
        """40001 failures are transient whether raw, chained via __cause__, or via __context__."""
        job = self._create_job()
        self.assertTrue(job._is_transient_error(self._serialization_error()))
        # Wrapped with an explicit cause (raise ... from) ...
        try:
            try:
                raise self._serialization_error()
            except psycopg2.errors.SerializationFailure as exc:
                raise ValueError("wrapped") from exc
        except ValueError as chained:
            self.assertTrue(job._is_transient_error(chained))
        # ... and with implicit chaining (__context__)
        try:
            try:
                raise self._serialization_error()
            except psycopg2.errors.SerializationFailure:
                raise ValueError("implicitly chained")
        except ValueError as chained_ctx:
            self.assertTrue(job._is_transient_error(chained_ctx))
        # Unrelated exceptions, and plain strings that merely contain the phrase, are NOT transient
        self.assertFalse(job._is_transient_error(ValueError("boom")))
        self.assertFalse(job._is_transient_error("could not serialize access due to concurrent update"))

    def test_transient_error_backs_off_and_reenqueues(self):
        """A serialization failure re-enqueues with a future backoff gate and schedules a wake-up."""
        job = self._create_job(name="Transient Job", state="running", max_retries=3)
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"), patch.object(
            type(self.env["base.bg"]), "_trigger_crons"
        ) as mock_trigger:
            requeued = job._handle_job_error(self._serialization_error())

        self.assertTrue(requeued)
        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.transient_retry_count, 1)
        self.assertEqual(job.retry_count, 1)
        self.assertTrue(job.next_retry_at, "A backoff gate must be set for transient errors")
        self.assertGreater(job.next_retry_at, fields.Datetime.now())
        # A wake-up is scheduled for when the backoff elapses.
        mock_trigger.assert_called_once()
        self.assertIn("at", mock_trigger.call_args.kwargs)

    def test_transient_error_does_not_consume_normal_retry_budget(self):
        """Serialization retries use their own budget (default 10), not max_retries (3)."""
        job = self._create_job(
            name="Persistent Transient", state="running", max_retries=3, retry_count=5, transient_retry_count=5
        )
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"), patch.object(
            type(self.env["base.bg"]), "_trigger_crons"
        ):
            requeued = job._handle_job_error(self._serialization_error())

        self.assertTrue(requeued)
        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")  # not failed despite retry_count > max_retries
        self.assertEqual(job.transient_retry_count, 6)

    def test_transient_error_fails_after_serialization_cap(self):
        """Once the serialization retry budget is exhausted, the job fails permanently."""
        self._set_param("base_bg.transient_max_retries", "3")
        job = self._create_job(name="Exhausted Transient", state="running", retry_count=2, transient_retry_count=2)
        with patch("odoo.addons.base_bg.models.bg_job._logger.error"):
            requeued = job._handle_job_error(self._serialization_error())

        self.assertFalse(requeued)
        job.invalidate_recordset()
        self.assertEqual(job.state, "failed")

    def test_non_transient_error_keeps_immediate_retry(self):
        """Non-serialization errors keep the original retry-then-fail behavior, no backoff gate."""
        job = self._create_job(name="Real Error Job", state="running", max_retries=2)
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"):
            requeued = job._handle_job_error("Some real failure")

        self.assertTrue(requeued)
        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.transient_retry_count, 0)
        self.assertFalse(job.next_retry_at, "Non-transient retries must not set a backoff gate")

    def test_transient_retries_do_not_starve_real_error_budget(self):
        """A job that burned transient retries still gets its full non-transient budget."""
        job = self._create_job(name="Mixed", state="running", max_retries=3, retry_count=4, transient_retry_count=4)
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"):
            requeued = job._handle_job_error("A genuine business error")

        self.assertTrue(requeued, "the first real error must retry even after transient retries")
        job.invalidate_recordset()
        self.assertEqual(job.state, "enqueued")
        self.assertEqual(job.retry_count, 5)  # non-transient attempts = 5 - 4 = 1 < max_retries(3)

    def test_malformed_int_param_falls_back_to_default(self):
        """A non-integer system parameter must not crash the runner; it falls back to the default."""
        self._set_param("base_bg.transient_max_retries", "not-a-number")
        with patch("odoo.addons.base_bg.models.bg_job._logger.warning"):
            self.assertEqual(self.BgJob._get_transient_max_retries(), 10)

    def test_fail_and_cancel_clear_backoff_gate(self):
        """fail() and cancel() clear next_retry_at so no stale gate lingers on the row."""
        future = fields.Datetime.now() + timedelta(minutes=5)
        job = self._create_job(name="Fail Clears Gate", state="running", next_retry_at=future)
        job.fail("done for", notify=False)
        job.invalidate_recordset()
        self.assertFalse(job.next_retry_at)

        job2 = self._create_job(name="Cancel Clears Gate", state="enqueued", next_retry_at=future)
        job2.cancel("nope")
        job2.invalidate_recordset()
        self.assertFalse(job2.next_retry_at)

    def test_get_next_job_skips_jobs_in_backoff(self):
        """Jobs whose backoff window is still in the future are not picked up."""
        self.BgJob.search([("state", "=", "enqueued")]).write({"state": "canceled"})
        future = fields.Datetime.now() + timedelta(minutes=10)
        self._create_job(name="Backing Off", state="enqueued", next_retry_at=future)
        self.assertEqual(self.BgJob._get_next_job(), self.env["bg.job"])

        eligible = self._create_job(name="Ready", state="enqueued")
        self.assertEqual(self.BgJob._get_next_job(), eligible)

    def test_finish_does_not_trigger_cron(self):
        """finish() must not hammer the cron on every completed job."""
        job = self._create_job(name="Finish No Trigger", state="running")
        with patch.object(type(self.env["base.bg"]), "_trigger_crons") as mock_trigger:
            job.finish()

        job.invalidate_recordset()
        self.assertEqual(job.state, "done")
        mock_trigger.assert_not_called()

    def test_finish_enqueues_next_and_marks_it_eligible(self):
        """finish() enqueues the next batch job, which the runner then sees as eligible."""
        self.BgJob.search([("state", "=", "enqueued")]).write({"state": "canceled"})
        job1 = self._create_job(name="Batch head", state="running")
        job2 = self._create_job(name="Batch tail", state="waiting")
        job1.next_job_id = job2
        job1.finish()

        job2.invalidate_recordset()
        self.assertEqual(job2.state, "enqueued")
        self.assertTrue(self.BgJob._has_eligible_jobs(), "the freshly-enqueued next job must be pickable")

    def test_run_releases_orm_cache(self):
        """run() drops the ORM cache after each job (success and error) to flatten the
        long-lived runner's memory between jobs."""
        # Success path
        partner = self.env["res.partner"].create({"name": "Mem partner"})
        ok_job = self._create_job(
            name="Mem OK",
            state="running",
            model="res.partner",
            method="exists",
            kwargs_json={"_record_ids": [partner.id]},
        )
        with patch.object(self.env.cr, "commit"), patch.object(type(ok_job), "_notify_user"), patch.object(
            type(self.env), "invalidate_all"
        ) as mock_inv:
            ok_job.run()
        mock_inv.assert_called()

        # Error path
        err_job = self._create_job(
            name="Mem ERR",
            state="running",
            model="bg.job",
            method="dummy_boom",
            kwargs_json={"_record_ids": [ok_job.id]},
        )
        with patch.object(type(err_job), "dummy_boom", create=True, side_effect=ValueError("boom")), patch.object(
            self.env.cr, "commit"
        ), patch.object(self.env.cr, "rollback"), patch(
            "odoo.addons.base_bg.models.bg_job._logger.warning"
        ), patch.object(type(self.env), "invalidate_all") as mock_inv_err:
            err_job.run()
        mock_inv_err.assert_called()
