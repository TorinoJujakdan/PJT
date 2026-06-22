import logging
from django.core.management import call_command

logger = logging.getLogger(__name__)

def sync_opinet_job():
    logger.info("Starting scheduled Opinet prices synchronization...")
    try:
        call_command("sync_opinet_prices")
        logger.info("Scheduled Opinet prices synchronization completed successfully.")
    except Exception as e:
        logger.error("Error executing scheduled Opinet prices synchronization: %s", e, exc_info=True)

def sync_cards_job():
    logger.info("Starting scheduled Naver Card benefits synchronization...")
    try:
        call_command("ingest_card_search", "--limit=30")
        logger.info("Scheduled Naver Card benefits synchronization completed successfully.")
    except Exception as e:
        logger.error("Error executing scheduled card benefits ingestion: %s", e, exc_info=True)


def start_scheduler():
    # Django runs ready() twice when using the auto-reloader (RUN_MAIN is not set in the parent).
    # We only want to run in the reloader's child process.
    # In production/deployment, RUN_MAIN will not be set, so we also allow if RUN_MAIN is not set but we're not using the reloader.
    # To handle both local dev and production:
    # 1. If we are in dev server (which sets RUN_MAIN), make sure RUN_MAIN is true.
    # 2. Prevent starting multiple schedulers in the same process using a function attribute guard.
    if hasattr(start_scheduler, "_started") and start_scheduler._started:
        return
    start_scheduler._started = True

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore, register_events
        from django.db import connection

        # Check if django-apscheduler database tables exist before trying to add jobs (resilience for initial migrations/tests)
        table_names = connection.introspection.table_names()
        if "django_apscheduler_djangojob" not in table_names:
            logger.warning("APScheduler database tables not yet migrated. Skipping scheduler initialization.")
            return

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Register sync_opinet_prices job to run at 05:01 and 17:01 every day
        scheduler.add_job(
            sync_opinet_job,
            trigger="cron",
            hour="5,17",
            minute=1,
            id="sync_opinet_prices_daily",
            max_instances=1,
            replace_existing=True,
        )

        # Register sync_card_benefits_daily job to run at 03:00 every day
        scheduler.add_job(
            sync_cards_job,
            trigger="cron",
            hour=3,
            minute=0,
            id="sync_card_benefits_daily",
            max_instances=1,
            replace_existing=True,
        )

        register_events(scheduler)
        scheduler.start()
        logger.info("APScheduler initialized successfully. Opinet prices daily (05:01, 17:01) & Card benefits daily (03:00) scheduled.")
    except Exception as e:
        logger.error("Failed to start APScheduler: %s", e, exc_info=True)
