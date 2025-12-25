"""
Cleanup Task

Celery beat task for periodic cleanup of expired jobs and files.
Thin wrapper that delegates to application services.
"""

import logging
import shutil
import os
from datetime import datetime
from pathlib import Path

from celery_app import celery_app

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.tasks.cleanup_expired_jobs")
def cleanup_expired_jobs(self):
    """
    Periodic cleanup task that removes expired jobs and associated files.

    Thin wrapper that delegates to JobService and FileManager for cleanup operations.
    This task only accesses application services through DependencyContainer,
    never infrastructure directly, maintaining proper layer separation.

    This task runs every 5 minutes (configured in Celery beat schedule) and:
    1. Cleans up expired jobs through JobService (which handles archival and file cleanup)
    2. Cleans up expired files through FileManager (proactive cleanup of any remaining expired files)
    3. Cleans up orphaned temporary files
    4. Logs cleanup activities for monitoring

    Returns:
        dict: Cleanup statistics with counts and errors

    """
    logger.info("Starting cleanup task")

    cleanup_stats = {
        "expired_jobs_removed": 0,
        "expired_files_cleaned": 0,
        "orphaned_files_cleaned": 0,
        "errors": [],
    }

    try:
        # Get services from DependencyContainer (Requirement 4.3)
        # This is the ONLY way to access services in tasks - never instantiate directly
        from celery_app import flask_app
        from src.application.job_service import JobService
        from src.domain.file_storage import FileManager

        container = flask_app.container
        job_service = container.resolve(JobService)
        file_manager = container.resolve(FileManager)

        # 1. Clean up expired jobs through JobService
        # JobService handles both job deletion and associated file cleanup
        logger.info("Cleaning up expired jobs...")
        try:
            jobs_cleaned = job_service.cleanup_expired_jobs(expiration_hours=1)
            cleanup_stats["expired_jobs_removed"] = jobs_cleaned
            logger.info(f"Cleaned up {jobs_cleaned} expired jobs")

        except Exception as e:
            error_msg = f"Error cleaning up expired jobs: {e}"
            cleanup_stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

        # 2. Clean up expired files through FileManager (Requirements 2.1, 2.2)
        # This proactively removes expired files and their metadata
        logger.info("Cleaning up expired files...")
        try:
            files_cleaned = file_manager.cleanup_expired_files()
            cleanup_stats["expired_files_cleaned"] = files_cleaned
            logger.info(f"Cleaned up {files_cleaned} expired files")

        except Exception as e:
            error_msg = f"Error cleaning up expired files: {e}"
            cleanup_stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

        # 3. Clean up orphaned temporary files in /tmp/downloaded_files
        logger.info("Cleaning up orphaned temporary files...")
        try:
            orphaned_count = _cleanup_orphaned_files()
            cleanup_stats["orphaned_files_cleaned"] = orphaned_count
            logger.info(f"Cleaned up {orphaned_count} orphaned files")

        except Exception as e:
            error_msg = f"Error cleaning up orphaned files: {e}"
            cleanup_stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

        # Log cleanup summary
        logger.info(
            f"Cleanup completed - Jobs: {cleanup_stats['expired_jobs_removed']}, "
            f"Files: {cleanup_stats['expired_files_cleaned']}, "
            f"Orphaned: {cleanup_stats['orphaned_files_cleaned']}, "
            f"Errors: {len(cleanup_stats['errors'])}"
        )

        if cleanup_stats["errors"]:
            logger.warning(f"Cleanup errors: {cleanup_stats['errors']}")

        return cleanup_stats

    except Exception as e:
        error_msg = f"Cleanup task failed: {e}"
        logger.error(error_msg, exc_info=True)
        return {
            "expired_jobs_removed": 0,
            "expired_files_cleaned": 0,
            "orphaned_files_cleaned": 0,
            "errors": [error_msg],
        }


def _cleanup_orphaned_files() -> int:
    """
    Clean up orphaned temporary files in /tmp/downloaded_files.

    Removes files and directories older than 1 hour, and empty directories.

    Returns:
        Number of items cleaned up
    """
    temp_dir = Path(os.getenv("DOWNLOAD_DIR", "/tmp/downloaded_files"))
    count = 0

    if not temp_dir.exists():
        return count

    current_time = datetime.utcnow()

    for item in temp_dir.iterdir():
        try:
            # Check item age
            item_age_seconds = current_time.timestamp() - item.stat().st_mtime

            # Remove items older than 1 hour
            if item_age_seconds > 3600:
                if item.is_file():
                    item.unlink()
                    count += 1
                    logger.info(f"Removed orphaned file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
                    logger.info(f"Removed orphaned directory: {item}")

        except OSError as e:
            logger.warning(f"Failed to remove orphaned item {item}: {e}")

    return count
