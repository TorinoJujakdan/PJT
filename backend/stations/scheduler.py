import logging

from django.conf import settings
from django.core.management import call_command
from django.db import connection

logger = logging.getLogger(__name__)


def sync_opinet_job():
    logger.info("Starting scheduled Opinet prices synchronization...")
    try:
        call_command("sync_opinet_prices")
        logger.info("Scheduled Opinet prices synchronization completed successfully.")
    except Exception as e:
        logger.error("Error executing scheduled Opinet prices synchronization: %s", e, exc_info=True)


def register_scheduled_jobs(scheduler):
    # Opinet prices still refresh automatically at 05:01 and 17:01.
    scheduler.add_job(
        sync_opinet_job,
        trigger="cron",
        hour="5,17",
        minute=1,
        id="sync_opinet_prices_daily",
        max_instances=1,
        replace_existing=True,
    )


def build_scheduler():
    """Build the dedicated scheduler process after Django is fully initialized."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from django_apscheduler.jobstores import DjangoJobStore, register_events

    table_names = connection.introspection.table_names()
    if "django_apscheduler_djangojob" not in table_names:
        raise RuntimeError(
            "APScheduler tables are missing. Run `python manage.py migrate` first."
        )

    scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    register_scheduled_jobs(scheduler)
    register_events(scheduler)
    return scheduler
