from django.test import SimpleTestCase

from stations.scheduler import register_scheduled_jobs


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
