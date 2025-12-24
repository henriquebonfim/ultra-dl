"""
Celery Configuration

Configures Celery with Flask integration, Redis broker, and task routing.
"""

import os

from celery import Celery
from kombu import Queue


class CeleryConfig:
    """Celery configuration settings."""

    # Broker settings
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Task settings
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"
    timezone = "UTC"
    enable_utc = True

    # Worker settings
    worker_prefetch_multiplier = 1
    task_acks_late = True
    worker_max_tasks_per_child = 50

    # Task routing
    task_routes = {
        "tasks.download_video": {"queue": "download_queue"},
        "tasks.cleanup_expired_jobs": {"queue": "cleanup_queue"},
    }

    # Queue definitions
    task_default_queue = "default"
    task_queues = (
        Queue("default", routing_key="default"),
        Queue("download_queue", routing_key="download"),
        Queue("cleanup_queue", routing_key="cleanup"),
    )

    # Beat schedule for periodic tasks
    beat_schedule = {
        "cleanup-expired-jobs": {
            "task": "tasks.cleanup_expired_jobs",
            "schedule": 300.0,  # Run every 5 minutes
        },
    }

    # Task time limits (in seconds)
    # Allow longer downloads for slow connections or large files
    task_soft_time_limit = int(
        os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", 5400)
    )  # 90 minutes default
    task_time_limit = int(
        os.getenv("CELERY_TASK_TIME_LIMIT", 6000)
    )  # 100 minutes default

    # Result backend settings
    result_expires = 3600  # 1 hour

    # Worker concurrency (for free tier resource limits)
    worker_concurrency = int(os.getenv("CELERY_WORKER_CONCURRENCY", 2))


def make_celery(app):
    """
    Create Celery instance with Flask app context.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery instance
    """
    celery = Celery(
        app.import_name,
        backend=CeleryConfig.result_backend,
        broker=CeleryConfig.broker_url,
    )

    # Update Celery config from our config class
    celery.config_from_object(CeleryConfig)

    # Ensure tasks run within Flask app context
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
