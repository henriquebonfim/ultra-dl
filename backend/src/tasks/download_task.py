"""
Download Task

Celery task for asynchronous video downloading.
Thin wrapper that delegates to DownloadService.
"""

import logging
from typing import Any, Dict

from celery_app import celery_app

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.tasks.download_video")
def download_video(
    self,
    job_id: str,
    url: str,
    format_id: str,
    start_time: float = None,
    end_time: float = None,
    quality: str = None,
    format_str: str = None,
    mute_audio: bool = False,
    mute_video: bool = False,
) -> Dict[str, Any]:
    """
    Asynchronous video download task.

    Thin wrapper that delegates to DownloadService for orchestration.
    Updates Celery task state with progress information.

    This task only accesses application services through DependencyContainer,
    never infrastructure directly, maintaining proper layer separation.

    Args:
        job_id: Unique job identifier
        url: YouTube URL to download
        format_id: Format ID for yt-dlp

    Returns:
        dict: Task result with status and file information
    """
    import time

    from src.application.download_service import DownloadService
    from src.domain.job_management.value_objects import JobProgress

    # Record task start time
    task_start_time = time.time()

    # Log task start
    logger.info(f"Task started for job {job_id}")

    # Get download service from DependencyContainer (Requirement 4.3)
    # This is the ONLY way to access services in tasks - never instantiate directly
    from celery_app import flask_app

    container = flask_app.container
    download_service = container.resolve(DownloadService)

    # Progress callback for Celery state updates
    def progress_callback(progress: JobProgress) -> None:
        """Update Celery task state with progress information."""
        self.update_state(
            state="PROGRESS",
            meta={
                "percentage": progress.percentage,
                "phase": progress.phase,
                "speed": progress.speed,
                "eta": progress.eta,
            },
        )

    try:
        # Execute download workflow
        # Execute download workflow
        result = download_service.execute_download(
            job_id=job_id,
            url=url,
            format_id=format_id,
            progress_callback=progress_callback,
            start_time=start_time,
            end_time=end_time,
            quality=quality,
            format_str=format_str,
            mute_audio=mute_audio,
            mute_video=mute_video,
        )

        # Calculate task duration
        duration_ms = (time.time() - task_start_time) * 1000

        # Log task completion
        logger.info(f"Task completed for job {job_id} in {duration_ms:.2f}ms")

        # Serialize result for task return (API layer responsibility)
        return {
            "success": result.success,
            "file_path": result.file_path,
            "error_message": result.error_message,
            "error_type": result.error_type,
        }

    except Exception as e:
        # Calculate task duration even on failure
        duration_ms = (time.time() - task_start_time) * 1000

        # Log task failure
        logger.error(f"Task failed for job {job_id} after {duration_ms:.2f}ms: {e}")

        # Re-raise exception
        raise
