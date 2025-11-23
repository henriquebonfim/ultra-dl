"""
Job Management Repositories

Repository interface for job persistence.
Concrete implementations are in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List, Optional

from .entities import DownloadJob
from .value_objects import JobProgress, JobStatus


class JobRepository(ABC):
    """Abstract repository interface for job persistence."""

    @abstractmethod
    def save(self, job: DownloadJob) -> bool:
        """
        Save or update a job.

        Args:
            job: DownloadJob to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get(self, job_id: str) -> Optional[DownloadJob]:
        """
        Retrieve a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            DownloadJob if found, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    def update_progress(self, job_id: str, progress: JobProgress) -> bool:
        """
        Atomically update job progress.

        Args:
            job_id: Job identifier
            progress: New progress information

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def update_status(
        self, job_id: str, status: JobStatus, error_message: Optional[str] = None
    ) -> bool:
        """
        Atomically update job status.

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message for failed jobs

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_expired_jobs(self, expiration_time: timedelta) -> List[str]:
        """
        Get list of job IDs that have expired.

        Args:
            expiration_time: Time delta for expiration

        Returns:
            List of expired job IDs
        """
        pass

    @abstractmethod
    def exists(self, job_id: str) -> bool:
        """
        Check if job exists.

        Args:
            job_id: Job identifier

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def get_many(self, job_ids: List[str]) -> List[DownloadJob]:
        """
        Retrieve multiple jobs by their IDs in a single operation.

        This method provides efficient batch retrieval of jobs, reducing
        network round trips when multiple jobs need to be fetched.

        Args:
            job_ids: List of job identifiers to retrieve

        Returns:
            List of DownloadJob instances for jobs that were found.
            Jobs that don't exist are silently omitted from the result.
            The order of returned jobs may not match the input order.

        Example:
            >>> jobs = repository.get_many(['job-1', 'job-2', 'job-3'])
            >>> print(f"Retrieved {len(jobs)} jobs")
        """
        pass

    @abstractmethod
    def save_many(self, jobs: List[DownloadJob]) -> bool:
        """
        Save or update multiple jobs in a single atomic operation.

        This method provides efficient batch persistence of jobs, reducing
        network round trips and ensuring atomicity when multiple jobs need
        to be saved together.

        Args:
            jobs: List of DownloadJob instances to save

        Returns:
            True if all jobs were successfully saved, False if any save failed.
            On failure, implementations should attempt to rollback changes to
            maintain consistency.

        Example:
            >>> jobs = [job1, job2, job3]
            >>> success = repository.save_many(jobs)
            >>> if success:
            ...     print("All jobs saved successfully")
        """
        pass

    @abstractmethod
    def find_by_status(self, status: JobStatus, limit: int = 100) -> List[DownloadJob]:
        """
        Find jobs by their current status.

        This method allows querying jobs based on their status, useful for
        monitoring, cleanup operations, or batch processing of jobs in
        specific states.

        Args:
            status: The JobStatus to filter by (e.g., PENDING, PROCESSING, COMPLETED)
            limit: Maximum number of jobs to return (default: 100).
                   Prevents unbounded result sets for large datasets.

        Returns:
            List of DownloadJob instances matching the status criteria.
            Returns empty list if no jobs match.
            Results are not guaranteed to be in any particular order.

        Example:
            >>> failed_jobs = repository.find_by_status(JobStatus.FAILED, limit=50)
            >>> print(f"Found {len(failed_jobs)} failed jobs")
        """
        pass
