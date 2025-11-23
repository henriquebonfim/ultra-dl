"""
Cleanup Task

Celery beat task for periodic cleanup of expired jobs and files.
Handles both local filesystem and Google Cloud Storage cleanup.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from celery_app import celery_app
from flask import current_app
from application.job_service import JobService
from domain.file_storage import FileManager
from infrastructure.gcs_storage_repository import GCSStorageRepository

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.cleanup_expired_jobs")
def cleanup_expired_jobs(self):
    """
    Periodic cleanup task that removes expired jobs and associated files.

    This task runs every 5 minutes (configured in Celery beat schedule) and:
    1. Cleans up expired files through FileManager
    2. Cleans up expired jobs through JobService
    3. Cleans up orphaned temporary files
    4. Logs cleanup activities for monitoring

    Returns:
        dict: Cleanup statistics with counts and errors
        
    Requirements: 6.1, 6.3, 6.5
    """
    logger.info("Starting cleanup task")

    cleanup_stats = {
        "expired_jobs_removed": 0,
        "expired_files_removed": 0,
        "orphaned_files_cleaned": 0,
        "errors": [],
    }

    try:
        # Push Flask app context for container access
        with current_app.app_context():
            # Get services from container using DependencyContainer
            container = current_app.container
            job_service = container.resolve(JobService)
            file_manager = container.resolve(FileManager)
            storage_repository = container.get_storage_repository()

            # 1. Clean up expired files through FileManager
            logger.info("Cleaning up expired files...")
            try:
                # Get expired files before cleanup for GCS handling
                expired_files = file_manager.file_repo.get_expired_files()
                
                # Handle GCS files separately using storage repository (infrastructure concern)
                if isinstance(storage_repository, GCSStorageRepository):
                    for file in expired_files:
                        if file.file_path.startswith("downloads/"):
                            # GCS file - delete from cloud storage using storage repository
                            blob_name = file.file_path
                            try:
                                if storage_repository.delete(blob_name):
                                    logger.info(f"Deleted GCS blob: {blob_name}")
                                else:
                                    error_msg = f"Failed to delete GCS blob: {blob_name}"
                                    cleanup_stats["errors"].append(error_msg)
                                    logger.warning(error_msg)
                            except Exception as e:
                                error_msg = f"Error deleting GCS blob {blob_name}: {e}"
                                cleanup_stats["errors"].append(error_msg)
                                logger.warning(error_msg)
                
                # Use FileManager to clean up expired files (handles local files and metadata)
                files_cleaned = file_manager.cleanup_expired_files()
                cleanup_stats["expired_files_removed"] = files_cleaned
                logger.info(f"Cleaned up {files_cleaned} expired files")
                
            except Exception as e:
                error_msg = f"Error cleaning up expired files: {e}"
                cleanup_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 2. Clean up expired jobs through JobService
            logger.info("Cleaning up expired jobs...")
            try:
                jobs_cleaned = job_service.cleanup_expired_jobs(expiration_hours=1)
                cleanup_stats["expired_jobs_removed"] = jobs_cleaned
                logger.info(f"Cleaned up {jobs_cleaned} expired jobs")
                
            except Exception as e:
                error_msg = f"Error cleaning up expired jobs: {e}"
                cleanup_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 3. Clean up orphaned temporary files in /tmp/ultra-dl
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
            f"Files: {cleanup_stats['expired_files_removed']}, "
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
            "expired_files_removed": 0,
            "orphaned_files_cleaned": 0,
            "errors": [error_msg],
        }


def _cleanup_orphaned_files() -> int:
    """
    Clean up orphaned temporary files in /tmp/ultra-dl.
    
    Removes files and directories older than 1 hour, and empty directories.
    
    Returns:
        Number of items cleaned up
    """
    temp_dir = Path("/tmp/ultra-dl")
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
            elif item.is_dir() and not any(item.iterdir()):
                # Remove empty directories regardless of age
                item.rmdir()
                logger.info(f"Removed empty directory: {item}")
                
        except OSError as e:
            logger.warning(f"Failed to remove orphaned item {item}: {e}")
    
    return count