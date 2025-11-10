"""
Celery Application Instance

Creates the Celery app instance for use by workers and beat scheduler.
"""

from config.celery_config import make_celery
from config.redis_config import init_redis
from flask import Flask


def create_app():
    """Create Flask app with Celery integration."""
    app = Flask(__name__)

    # Initialize Redis
    init_redis()

    # Create Celery instance
    celery = make_celery(app)

    # Store celery instance on app for access in routes
    app.celery = celery

    return app, celery


# Create app and celery instances
flask_app, celery_app = create_app()

# Register task module imports on the Celery instance by name to avoid
# importing task modules at module-import time (which caused a circular
# import: tasks -> download_task -> celery_app -> tasks).
# The worker will import these modules when it starts, at which point
# `celery_app` is already initialized and available for task decorators.
celery_app.conf.imports = (
    "tasks.download_task",
    "tasks.cleanup_task",
)
