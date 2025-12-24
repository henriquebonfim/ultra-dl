"""
WebSocket Event Handler

Infrastructure event handler for emitting WebSocket messages for domain events.
Translates domain events into WebSocket messages for real-time client notifications.
"""

import logging

from src.api.websocket_events import (
    emit_job_completed,
    emit_job_failed,
    emit_job_progress,
)
from src.config.socketio_config import is_socketio_enabled
from src.domain.events import (
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent,
    JobStartedEvent,
)

logger = logging.getLogger(__name__)


class WebSocketEventHandler:
    """
    Event handler that emits WebSocket messages for domain events.

    This handler translates domain events into WebSocket messages for
    real-time client notifications. It checks if SocketIO is enabled
    before attempting to emit messages.
    """

    def handle_job_started(self, event: JobStartedEvent) -> None:
        """
        Handle JobStartedEvent by emitting WebSocket notification.

        Args:
            event: JobStartedEvent containing job start information
        """
        if not is_socketio_enabled():
            logger.debug("SocketIO disabled, skipping job_started emission")
            return

        try:
            logger.info(
                f"Job {event.aggregate_id} started: url={event.url}, "
                f"format_id={event.format_id}"
            )

        except Exception as e:
            logger.error(
                f"Error handling JobStartedEvent for job {event.aggregate_id}: {e}",
                exc_info=True,
            )

    def handle_job_progress(self, event: JobProgressUpdatedEvent) -> None:
        """
        Handle JobProgressUpdatedEvent by emitting WebSocket notification.

        Args:
            event: JobProgressUpdatedEvent containing progress information
        """
        if not is_socketio_enabled():
            logger.debug("SocketIO disabled, skipping job_progress emission")
            return

        try:
            progress_data = event.progress.to_dict()

            logger.debug(
                f"Job {event.aggregate_id} progress: {progress_data.get('percent', 0)}%"
            )

            emit_job_progress(event.aggregate_id, progress_data)

        except Exception as e:
            logger.error(
                f"Error handling JobProgressUpdatedEvent for job {event.aggregate_id}: {e}",
                exc_info=True,
            )

    def handle_job_completed(self, event: JobCompletedEvent) -> None:
        """
        Handle JobCompletedEvent by emitting WebSocket notification.

        Args:
            event: JobCompletedEvent containing completion information
        """
        if not is_socketio_enabled():
            logger.debug("SocketIO disabled, skipping job_completed emission")
            return

        try:
            logger.info(
                f"Job {event.aggregate_id} completed: "
                f"download_url={event.download_url}"
            )

            emit_job_completed(event.aggregate_id, event.download_url, event.expire_at)

        except Exception as e:
            logger.error(
                f"Error handling JobCompletedEvent for job {event.aggregate_id}: {e}",
                exc_info=True,
            )

    def handle_job_failed(self, event: JobFailedEvent) -> None:
        """
        Handle JobFailedEvent by emitting WebSocket notification.

        Args:
            event: JobFailedEvent containing failure information
        """
        if not is_socketio_enabled():
            logger.debug("SocketIO disabled, skipping job_failed emission")
            return

        try:
            logger.warning(
                f"Job {event.aggregate_id} failed: "
                f"error={event.error_message}, category={event.error_category}"
            )

            emit_job_failed(
                event.aggregate_id, event.error_message, event.error_category
            )

        except Exception as e:
            logger.error(
                f"Error handling JobFailedEvent for job {event.aggregate_id}: {e}",
                exc_info=True,
            )
