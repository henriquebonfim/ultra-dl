"""
Cleanup Task

Celery beat task for periodic cleanup of expired jobs and files.
Handles both local filesystem and Google Cloud Storage cleanup.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from celery_app import celery_app
from config.redis_config import get_redis_repository
from domain.file_storage.repositories import RedisFileRepository
from domain.job_management.repositories import RedisJobRepository
from infrastructure.gcs_repository import GCSRepository

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.cleanup_expired_jobs")
def cleanup_expired_jobs(self):
    """
    Periodic cleanup task that removes expired jobs and associated files.

    This task runs every 5 minutes (configured in Celery beat schedule) and:
    1. Queries Redis for expired file tokens
    2. Deletes expired files from local storage or GCS
    3. Removes expired job records from Redis
    4. Cleans up orphaned temporary files
    5. Logs cleanup activities for monitoring

    Returns:
        dict: Cleanup statistics with counts and errors
    """
    logger.info("Starting cleanup task")

    cleanup_stats = {
        "expired_jobs_removed": 0,
        "expired_files_removed": 0,
        "local_files_cleaned": 0,
        "gcs_files_cleaned": 0,
        "orphaned_files_cleaned": 0,
        "errors": [],
    }

    try:
        # Initialize repositories
        redis_repo = get_redis_repository()
        file_repo = RedisFileRepository(redis_repo)
        job_repo = RedisJobRepository(redis_repo)
        gcs_repo = GCSRepository()

        # 1. Clean up expired files
        logger.info("Checking for expired files...")
        expired_files = file_repo.get_expired_files()

        for file in expired_files:
            try:
                logger.info(
                    f"Processing expired file: token={file.token}, job_id={file.job_id}"
                )

                # Determine if file is in GCS or local storage
                if file.file_path.startswith("downloads/"):
                    # GCS file - extract blob name from path
                    blob_name = file.file_path
                    if gcs_repo.is_available():
                        if gcs_repo.delete_blob(blob_name):
                            cleanup_stats["gcs_files_cleaned"] += 1
                            logger.info(f"Deleted GCS blob: {blob_name}")
                        else:
                            error_msg = f"Failed to delete GCS blob: {blob_name}"
                            cleanup_stats["errors"].append(error_msg)
                            logger.warning(error_msg)
                    else:
                        logger.warning(
                            f"GCS not available, cannot delete blob: {blob_name}"
                        )
                else:
                    # Local file
                    local_path = Path(file.file_path)
                    if local_path.exists():
                        try:
                            local_path.unlink()
                            cleanup_stats["local_files_cleaned"] += 1
                            logger.info(f"Deleted local file: {local_path}")
                        except OSError as e:
                            error_msg = f"Failed to delete local file {local_path}: {e}"
                            cleanup_stats["errors"].append(error_msg)
                            logger.error(error_msg)
                    else:
                        logger.debug(f"Local file already deleted: {local_path}")

                # Delete file metadata from Redis
                if file_repo.delete(file.token):
                    cleanup_stats["expired_files_removed"] += 1
                    logger.info(f"Removed file metadata for token: {file.token}")

            except Exception as e:
                error_msg = f"Error processing expired file {file.token}: {e}"
                cleanup_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

        # 2. Clean up expired jobs (completed/failed jobs older than 1 hour)
        logger.info("Checking for expired jobs...")
        expiration_time = timedelta(hours=1)
        expired_job_ids = job_repo.get_expired_jobs(expiration_time)

        for job_id in expired_job_ids:
            try:
                # Delete associated file if exists
                file = file_repo.get_by_job_id(job_id)
                if file:
                    # File cleanup will be handled by expired files check above
                    logger.debug(f"Job {job_id} has associated file: {file.token}")

                # Delete job record
                if job_repo.delete(job_id):
                    cleanup_stats["expired_jobs_removed"] += 1
                    logger.info(f"Removed expired job: {job_id}")

            except Exception as e:
                error_msg = f"Error processing expired job {job_id}: {e}"
                cleanup_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

        # 3. Clean up orphaned temporary files in /tmp/ultra-dl
        logger.info("Checking for orphaned temporary files...")
        temp_dir = Path("/tmp/ultra-dl")

        if temp_dir.exists():
            try:
                current_time = datetime.utcnow()

                for item in temp_dir.iterdir():
                    try:
                        # Check item age
                        item_age_seconds = current_time.timestamp() - item.stat().st_mtime

                        # Remove items older than 1 hour
                        if item_age_seconds > 3600:
                            if item.is_file():
                                item.unlink()
                                cleanup_stats["orphaned_files_cleaned"] += 1
                                logger.info(f"Removed orphaned file: {item}")
                            elif item.is_dir():
                                shutil.rmtree(item)
                                cleanup_stats["orphaned_files_cleaned"] += 1
                                logger.info(f"Removed orphaned directory: {item}")
                        elif item.is_dir() and not any(item.iterdir()):
                            # Remove empty directories regardless of age
                            item.rmdir()
                            logger.info(f"Removed empty directory: {item}")

                    except OSError as e:
                        error_msg = f"Failed to remove orphaned item {item}: {e}"
                        cleanup_stats["errors"].append(error_msg)
                        logger.warning(error_msg)

            except Exception as e:
                error_msg = f"Error cleaning temp directory: {e}"
                cleanup_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

        # Log cleanup summary
        logger.info(
            f"Cleanup completed - Jobs: {cleanup_stats['expired_jobs_removed']}, "
            f"Files: {cleanup_stats['expired_files_removed']}, "
            f"Local: {cleanup_stats['local_files_cleaned']}, "
            f"GCS: {cleanup_stats['gcs_files_cleaned']}, "
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
            "local_files_cleaned": 0,
            "gcs_files_cleaned": 0,
            "orphaned_files_cleaned": 0,
            "errors": [error_msg],
        }