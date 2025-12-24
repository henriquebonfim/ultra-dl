"""
Job Management Services

Domain services for job lifecycle management.
"""

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from src.domain.errors import DomainError

from .entities import DownloadJob, JobArchive
from .repositories import JobRepository, IJobArchiveRepository
from .value_objects import JobProgress

if TYPE_CHECKING:
    from ..file_storage.services import FileManager


class JobNotFoundError(DomainError):
    """Raised when a job is not found."""

    pass


class JobStateError(DomainError):
    """Raised when an invalid state transition is attempted."""

    pass


class JobManager:
    """
    Domain service for managing download job lifecycle.

    Coordinates job creation, status updates, and completion.
    """

    def __init__(
        self, 
        job_repository: JobRepository,
        archive_repository: Optional[IJobArchiveRepository] = None
    ):
        """
        Initialize JobManager with repositories.

        Args:
            job_repository: Repository for job persistence
            archive_repository: Optional repository for job archival
        """
        self.job_repo = job_repository
        self.archive_repo = archive_repository

    def create_job(self, url: str, format_id: str) -> DownloadJob:
        """
        Create a new download job.

        Args:
            url: YouTube URL
            format_id: Format ID to download

        Returns:
            Created DownloadJob

        Raises:
            Exception: If job creation fails
        """
        job = DownloadJob.create(url, format_id)

        if not self.job_repo.save(job):
            raise Exception("Failed to save job to repository")

        return job

    def get_job(self, job_id: str) -> DownloadJob:
        """
        Retrieve a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            DownloadJob

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = self.job_repo.get(job_id)

        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")

        return job

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
        job = self.get_job(job_id)

        try:
            job.start()
            if not self.job_repo.save(job):
                raise Exception("Failed to save job")
            return job
        except ValueError as e:
            raise JobStateError(str(e))

    def update_job_progress(self, job_id: str, progress: JobProgress) -> bool:
        """
        Update job progress atomically.

        Args:
            job_id: Job identifier
            progress: New progress information

        Returns:
            True if successful

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        if not self.job_repo.exists(job_id):
            raise JobNotFoundError(f"Job {job_id} not found")

        return self.job_repo.update_progress(job_id, progress)

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
        job = self.get_job(job_id)

        try:
            job.complete(download_url, download_token, expire_at)
            if not self.job_repo.save(job):
                raise Exception("Failed to save job")
            return job
        except ValueError as e:
            raise JobStateError(str(e))

    def fail_job(
        self, job_id: str, error_message: str, error_category: Optional[str] = None
    ) -> DownloadJob:
        """
        Mark job as failed.

        Args:
            job_id: Job identifier
            error_message: Error description
            error_category: Optional error category for tracking

        Returns:
            Updated DownloadJob

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = self.get_job(job_id)
        job.fail(error_message, error_category)

        if not self.job_repo.save(job):
            raise Exception("Failed to save job")

        return job

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted
        """
        return self.job_repo.delete(job_id)

    def cleanup_expired_jobs(
        self, 
        expiration_time: timedelta = timedelta(hours=1),
        file_manager: Optional['FileManager'] = None
    ) -> int:
        """
        Clean up expired jobs with archival.
        
        Process:
        1. Get expired job data
        2. Create and save archive (if archive_repo available)
        3. Delete associated file via FileManager (if file_manager provided)
        4. Delete job record
        
        Args:
            expiration_time: Time delta for expiration
            file_manager: Optional FileManager for coordinating file deletion
        
        Returns:
            Count of successfully cleaned jobs
            
        Note:
            Individual cleanup failures are handled gracefully - the method
            continues processing other jobs even if one fails. This ensures
            partial cleanup success rather than all-or-nothing behavior.
        """
        expired_job_ids = self.job_repo.get_expired_jobs(expiration_time)

        count = 0
        for job_id in expired_job_ids:
            try:
                # Step 1: Get job data for archival
                job = self.job_repo.get(job_id)
                if job is None:
                    # Job already deleted or doesn't exist, skip
                    continue
                
                # Step 2: Create and save archive (if archive repository available)
                if self.archive_repo and job.is_terminal():
                    try:
                        archive = JobArchive.from_job(job)
                        archive_saved = self.archive_repo.save(archive)
                        if not archive_saved:
                            # Log would happen at application layer
                            # Continue with cleanup even if archive fails
                            pass
                    except Exception:
                        # Archive creation/save failed, but continue with cleanup
                        # Application layer can track these failures if needed
                        pass
                
                # Step 3: Delete associated file (if file_manager provided)
                if file_manager:
                    try:
                        file_manager.delete_file_by_job_id(job.job_id)
                    except Exception:
                        # File deletion failed, but continue with job cleanup
                        # Application layer can track these failures if needed
                        pass
                
                # Step 4: Delete job record
                if self.job_repo.delete(job_id):
                    count += 1
                    
            except Exception:
                # Individual job cleanup failed, continue with others
                # Application layer can track these failures if needed
                continue

        return count

    def get_job_status_info(self, job_id: str) -> dict:
        """
        Get job status information for API response.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with job status information

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = self.get_job(job_id)

        # Calculate time remaining until expiration
        time_remaining = None
        if job.expire_at:
            remaining = (job.expire_at - datetime.utcnow()).total_seconds()
            time_remaining = max(0, int(remaining))  # Don't return negative values

        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress.to_dict(),
            "download_url": job.download_url,
            "expire_at": job.expire_at.isoformat() if job.expire_at else None,
            "time_remaining": time_remaining,
            "error": job.error_message,
            "error_category": job.error_category,
        }
