from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase

from stations.apps import StationsConfig
from stations.scheduler import build_scheduler, register_scheduled_jobs


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, *args, **kwargs):
        self.jobs.append(kwargs)


class SchedulerRegistrationTests(SimpleTestCase):
    def test_register_scheduled_jobs_does_not_register_card_ingestion_job(self):
        scheduler = FakeScheduler()

        register_scheduled_jobs(scheduler)

        job_ids = {job["id"] for job in scheduler.jobs}
        self.assertIn("sync_opinet_prices_daily", job_ids)
        self.assertNotIn("sync_card_benefits_daily", job_ids)

    def test_station_app_does_not_start_scheduler_during_app_initialization(self):
        self.assertNotIn("ready", StationsConfig.__dict__)

    @patch(
        "stations.scheduler.connection.introspection.table_names",
        return_value=[],
    )
    def test_build_scheduler_requires_migrations(self, _table_names):
        with self.assertRaisesRegex(RuntimeError, "manage.py migrate"):
            build_scheduler()

    @patch("stations.management.commands.run_scheduler.build_scheduler")
    def test_run_scheduler_command_owns_scheduler_lifecycle(self, build):
        scheduler = Mock()
        scheduler.start.side_effect = KeyboardInterrupt
        build.return_value = scheduler
        output = StringIO()

        call_command("run_scheduler", stdout=output)

        scheduler.start.assert_called_once_with()
        self.assertIn("scheduler started", output.getvalue())
        self.assertIn("scheduler stopped", output.getvalue())
