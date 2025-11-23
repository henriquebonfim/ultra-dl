"""
Celery Application Instance

Creates the Celery app instance for use by workers and beat scheduler.
Uses the app factory to ensure all services are properly initialized.
"""

from app_factory import create_app

# Create Flask app with all services initialized (including dependency container)
flask_app = create_app()

# Get Celery instance from Flask app
celery_app = flask_app.celery

# Register task module imports on the Celery instance by name to avoid
# importing task modules at module-import time (which caused a circular
# import: tasks -> download_task -> celery_app -> tasks).
# The worker will import these modules when it starts, at which point
# `celery_app` is already initialized and available for task decorators.
celery_app.conf.imports = (
    "tasks.download_task",
    "tasks.cleanup_task",
)
