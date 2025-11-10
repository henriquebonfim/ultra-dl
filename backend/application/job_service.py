"""
Job Application Service

Coordinates job management use cases.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from domain.file_storage import FileManager
from domain.job_management import (
    DownloadJob,
    JobManager,
    JobNotFoundError,
    JobProgress,
    JobStateError,
)

logger = logging.getLogger(__name__)


class JobService:
    """
    Application service for job management operations.

    Orchestrates job creation, status tracking, and lifecycle management.
    """

    def __init__(self, job_manager: JobManager, file_manager: FileManager):
        """
        Initialize JobService with job manager and file manager.

        Args:
            job_manager: JobManager domain service
            file_manager: FileManager for file operations
        """
        self.job_manager = job_manager
        self.file_manager = file_manager

    def create_download_job(self, url: str, format_id: str) -> Dict[str, Any]:
        """
        Create a new download job.

        Args:
            url: YouTube URL
            format_id: Format ID to download

        Returns:
            Dictionary with job information

        Raises:
            Exception: If job creation fails
        """
        try:
            logger.info(f"Creating download job for URL: {url}, format: {format_id}")

            job = self.job_manager.create_job(url, format_id)

            logger.info(f"Created job {job.job_id}")

            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "message": "Download job created successfully",
            }
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status information.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with job status

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        try:
            return self.job_manager.get_job_status_info(job_id)
        except JobNotFoundError:
            logger.warning(f"Job not found: {job_id}")
            raise
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {str(e)}")
            raise

    def start_job(self, job_id: str) -> DownloadJob:
        """
        Start a pending job.

        Args:
            job_id: Job identifier

        Returns:
            Updated DownloadJob

        Raises:
            JobNotFoundError: If job doesn't exist
            JobStateError: If job cannot be started
        """
        try:
            logger.info(f"Starting job {job_id}")

            job = self.job_manager.start_job(job_id)

            logger.info(f"Job {job_id} started successfully")

            return job
        except (JobNotFoundError, JobStateError) as e:
            logger.error(f"Error starting job {job_id}: {str(e)}")
            raise

    def update_progress(
        self,
        job_id: str,
        percentage: int,
        phase: str,
        speed: Optional[str] = None,
        eta: Optional[int] = None,
    ) -> bool:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            percentage: Progress percentage (0-100)
            phase: Current phase description
            speed: Download speed (optional)
            eta: Estimated time remaining in seconds (optional)

        Returns:
            True if successful

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        try:
            progress = JobProgress(
                percentage=percentage, phase=phase, speed=speed, eta=eta
            )

            success = self.job_manager.update_job_progress(job_id, progress)

            if success:
                logger.debug(
                    f"Updated progress for job {job_id}: {percentage}% - {phase}"
                )
            else:
                logger.warning(f"Failed to update progress for job {job_id}")

            return success
        except JobNotFoundError:
            logger.warning(f"Job not found when updating progress: {job_id}")
            raise
        except Exception as e:
            logger.error(f"Error updating progress for job {job_id}: {str(e)}")
            return False

    def complete_job(
        self,
        job_id: str,
        download_url: Optional[str] = None,
        download_token: Optional[str] = None,
        expire_at: Optional[datetime] = None,
    ) -> DownloadJob:
        """
        Mark job as completed.

        Args:
            job_id: Job identifier
            download_url: URL to download the file
            download_token: Token for file access
            expire_at: When the download URL expires

        Returns:
            Updated DownloadJob

        Raises:
            JobNotFoundError: If job doesn't exist
            JobStateError: If job cannot be completed
        """
        try:
            logger.info(f"Completing job {job_id}")

            job = self.job_manager.complete_job(
                job_id, download_url, download_token, expire_at
            )

            logger.info(f"Job {job_id} completed successfully")

            return job
        except (JobNotFoundError, JobStateError) as e:
            logger.error(f"Error completing job {job_id}: {str(e)}")
            raise

    def fail_job(self, job_id: str, error_message: str) -> DownloadJob:
        """
        Mark job as failed.

        Args:
            job_id: Job identifier
            error_message: Error description

        Returns:
            Updated DownloadJob

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        try:
            logger.error(f"Failing job {job_id}: {error_message}")

            job = self.job_manager.fail_job(job_id, error_message)

            return job
        except JobNotFoundError:
            logger.warning(f"Job not found when marking as failed: {job_id}")
            raise
        except Exception as e:
            logger.error(f"Error failing job {job_id}: {str(e)}")
            raise

    def cleanup_expired_jobs(self, expiration_hours: int = 1) -> int:
        """
        Clean up expired jobs.

        Args:
            expiration_hours: Hours after which jobs are considered expired

        Returns:
            Number of jobs cleaned up
        """
        try:
            expiration_time = timedelta(hours=expiration_hours)
            count = self.job_manager.cleanup_expired_jobs(expiration_time)

            if count > 0:
                logger.info(f"Cleaned up {count} expired jobs")

            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired jobs: {str(e)}")
            return 0

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and its associated file.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted
        """
        try:
            logger.info(f"Deleting job {job_id}")

            # Get the job to access download_token for file deletion
            try:
                job = self.job_manager.get_job(job_id)
                download_token = job.download_token

                # Delete the file if it exists
                if download_token:
                    file_deleted = self.file_manager.delete_file(download_token)
                    if file_deleted:
                        logger.info(f"File for job {job_id} deleted successfully")
                    else:
                        logger.warning(f"Failed to delete file for job {job_id}")
            except JobNotFoundError:
                logger.warning(f"Job {job_id} not found, skipping file deletion")

            # Delete the job record
            success = self.job_manager.delete_job(job_id)

            if success:
                logger.info(f"Job {job_id} deleted successfully")
            else:
                logger.warning(f"Failed to delete job {job_id}")

            return success
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            return False
