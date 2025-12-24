"""
WebSocket Helper Functions

Simple helper functions for emitting WebSocket events directly from application services.
Replaces the over-engineered EventPublisher pattern.
"""

import logging
from datetime import datetime
from typing import Optional

from src.api.websocket_events import (
    emit_job_completed,
    emit_job_failed,
    emit_job_progress,
    emit_job_warning,
)
from src.config.socketio_config import is_socketio_enabled
from src.domain.job_management.value_objects import JobProgress

logger = logging.getLogger(__name__)


def emit_websocket_job_progress(job_id: str, progress: JobProgress) -> None:
    """
    Emit WebSocket progress update for a job.

    Args:
        job_id: Job identifier
        progress: JobProgress value object with progress information
    """
    if not is_socketio_enabled():
        logger.debug("SocketIO disabled, skipping job_progress emission")
        return

    try:
        progress_data = progress.to_dict()
        logger.debug(f"Job {job_id} progress: {progress_data.get('percent', 0)}%")
        emit_job_progress(job_id, progress_data)
    except Exception as e:
        logger.error(
            f"Error emitting WebSocket progress for job {job_id}: {e}",
            exc_info=True,
        )


def emit_websocket_job_completed(
    job_id: str, download_url: str, expire_at: datetime
) -> None:
    """
    Emit WebSocket completion event for a job.

    Args:
        job_id: Job identifier
        download_url: URL to download the file
        expire_at: When the download URL expires
    """
    if not is_socketio_enabled():
        logger.debug("SocketIO disabled, skipping job_completed emission")
        return

    try:
        logger.info(f"Job {job_id} completed: download_url={download_url}")
        emit_job_completed(job_id, download_url, expire_at)
    except Exception as e:
        logger.error(
            f"Error emitting WebSocket completion for job {job_id}: {e}",
            exc_info=True,
        )


def emit_websocket_job_failed(
    job_id: str, error_message: str, error_category: Optional[str] = None
) -> None:
    """
    Emit WebSocket failure event for a job.

    Args:
        job_id: Job identifier
        error_message: Human-readable error message
        error_category: Error category for tracking and analytics
    """
    if not is_socketio_enabled():
        logger.debug("SocketIO disabled, skipping job_failed emission")
        return

    try:
        logger.warning(
            f"Job {job_id} failed: error={error_message}, category={error_category}"
        )
        emit_job_failed(job_id, error_message, error_category)
    except Exception as e:
        logger.error(
            f"Error emitting WebSocket failure for job {job_id}: {e}",
            exc_info=True,
        )


def emit_websocket_job_warning(job_id: str, message: str) -> None:
    """
    Emit WebSocket warning event for a job.

    Args:
        job_id: Job identifier
        message: Warning message to display to the user
    """
    if not is_socketio_enabled():
        logger.debug("SocketIO disabled, skipping job_warning emission")
        return

    try:
        logger.warning(f"Job {job_id} warning: {message}")
        emit_job_warning(job_id, message)
    except Exception as e:
        logger.error(
            f"Error emitting WebSocket warning for job {job_id}: {e}",
            exc_info=True,
        )


__all__ = [
    "emit_websocket_job_progress",
    "emit_websocket_job_completed",
    "emit_websocket_job_failed",
    "emit_websocket_job_warning",
]
