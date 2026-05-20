from django.apps import AppConfig


class StationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stations"

    def ready(self):
        # Prevent starting scheduler during management tasks like makemigrations/migrate/test in main thread
        import sys
        if "migrate" in sys.argv or "makemigrations" in sys.argv or "test" in sys.argv:
            return

        # Django runs ready() twice when using the auto-reloader (runserver).
        # We must only start the scheduler in the active child worker process (where RUN_MAIN == 'true').
        import os
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        from .scheduler import start_scheduler
        start_scheduler()


