"""
Download Task

Celery task for asynchronous video downloading.
Thin wrapper that delegates to DownloadService.
Requirements: 6.1, 6.2, 6.4
"""

import logging
from typing import Any, Dict

from celery_app import celery_app

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.download_video")
def download_video(self, job_id: str, url: str, format_id: str) -> Dict[str, Any]:
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
    from domain.job_management.value_objects import JobProgress
    from application.download_service import DownloadService
    
    # Record task start time
    start_time = time.time()
    
    # Log task start
    logger.info(f"Task started for job {job_id}")
    
    # Get download service from container (application layer only)
    from celery_app import flask_app
    container = flask_app.container
    download_service = container.resolve(DownloadService)
    
    # Progress callback for Celery state updates
    def progress_callback(progress: JobProgress) -> None:
        """Update Celery task state with progress information."""
        self.update_state(
            state='PROGRESS',
            meta={
                'percentage': progress.percentage,
                'phase': progress.phase,
                'speed': progress.speed,
                'eta': progress.eta
            }
        )
    
    try:
        # Execute download workflow
        result = download_service.execute_download(
            job_id=job_id,
            url=url,
            format_id=format_id,
            progress_callback=progress_callback
        )
        
        # Calculate task duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log task completion
        logger.info(f"Task completed for job {job_id} in {duration_ms:.2f}ms")
        
        # Return result dictionary
        return result.to_dict()
        
    except Exception as e:
        # Calculate task duration even on failure
        duration_ms = (time.time() - start_time) * 1000
        
        # Log task failure
        logger.error(f"Task failed for job {job_id} after {duration_ms:.2f}ms: {e}")
        
        # Re-raise exception
        raise
