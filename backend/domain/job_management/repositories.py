"""
Job Management Repositories

Repository interfaces and implementations for job persistence.
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
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


class RedisJobRepository(JobRepository):
    """
    Redis-based implementation of JobRepository.

    Provides atomic operations and distributed locking for job persistence.
    """

    def __init__(self, redis_repository):
        """
        Initialize with Redis repository.

        Args:
            redis_repository: RedisRepository instance from infrastructure layer
        """
        self.redis_repo = redis_repository
        self.key_prefix = "job"
        self.ttl = int(os.getenv("JOB_TTL_SECONDS", 3600))  # 1 hour TTL for jobs

    def save(self, job: DownloadJob) -> bool:
        """Save or update a job in Redis."""
        key = f"{self.key_prefix}:{job.job_id}"
        data = job.to_dict()
        return self.redis_repo.set_json(key, data, ttl=self.ttl)

    def get(self, job_id: str) -> Optional[DownloadJob]:
        """Retrieve a job from Redis."""
        key = f"{self.key_prefix}:{job_id}"
        data = self.redis_repo.get_json(key)

        if data is None:
            return None

        try:
            return DownloadJob.from_dict(data)
        except Exception as e:
            print(f"Error deserializing job {job_id}: {e}")
            return None

    def delete(self, job_id: str) -> bool:
        """Delete a job from Redis."""
        key = f"{self.key_prefix}:{job_id}"
        return self.redis_repo.delete(key)

    def update_progress(self, job_id: str, progress: JobProgress) -> bool:
        """
        Atomically update job progress using Redis transaction.

        This ensures thread-safe progress updates from multiple workers.
        """
        key = f"{self.key_prefix}:{job_id}"

        # Update progress and updated_at atomically
        progress_data = progress.to_dict()
        updated_at = datetime.utcnow().isoformat()

        # Use Lua script for atomic update
        lua_script = """
        local key = KEYS[1]
        local progress_json = ARGV[1]
        local updated_at = ARGV[2]

        local data = redis.call('GET', key)
        if not data then
            return 0
        end

        local job_data = cjson.decode(data)
        job_data['progress'] = cjson.decode(progress_json)
        job_data['updated_at'] = updated_at

        local updated_data = cjson.encode(job_data)
        redis.call('SET', key, updated_data)
        redis.call('EXPIRE', key, ARGV[3])
        return 1
        """

        try:
            import json

            result = self.redis_repo.redis.eval(
                lua_script,
                1,
                self.redis_repo._make_key(key),
                json.dumps(progress_data),
                updated_at,
                self.ttl,
            )
            return result == 1
        except Exception as e:
            print(f"Error updating progress for job {job_id}: {e}")
            return False

    def update_status(
        self, job_id: str, status: JobStatus, error_message: Optional[str] = None
    ) -> bool:
        """
        Atomically update job status.
        """
        key = f"{self.key_prefix}:{job_id}"
        updated_at = datetime.utcnow().isoformat()

        # Use Lua script for atomic update
        lua_script = """
        local key = KEYS[1]
        local status = ARGV[1]
        local updated_at = ARGV[2]
        local error_message = ARGV[3]

        local data = redis.call('GET', key)
        if not data then
            return 0
        end

        local job_data = cjson.decode(data)
        job_data['status'] = status
        job_data['updated_at'] = updated_at
        if error_message ~= '' then
            job_data['error_message'] = error_message
        end

        local updated_data = cjson.encode(job_data)
        redis.call('SET', key, updated_data)
        redis.call('EXPIRE', key, ARGV[4])
        return 1
        """

        try:
            result = self.redis_repo.redis.eval(
                lua_script,
                1,
                self.redis_repo._make_key(key),
                status.value,
                updated_at,
                error_message or "",
                self.ttl,
            )
            return result == 1
        except Exception as e:
            print(f"Error updating status for job {job_id}: {e}")
            return False

    def get_expired_jobs(self, expiration_time: timedelta) -> List[str]:
        """
        Get list of expired job IDs.

        Note: With Redis TTL, jobs are automatically deleted.
        This method finds jobs that are old but not yet expired by TTL.
        """
        pattern = f"{self.key_prefix}:*"
        keys = self.redis_repo.get_keys_by_pattern(pattern)

        expired_jobs = []
        cutoff_time = datetime.utcnow() - expiration_time

        for key in keys:
            job = self.get(key.replace(f"{self.key_prefix}:", ""))
            if job and job.updated_at < cutoff_time and job.is_terminal():
                expired_jobs.append(job.job_id)

        return expired_jobs

    def exists(self, job_id: str) -> bool:
        """Check if job exists in Redis."""
        key = f"{self.key_prefix}:{job_id}"
        return self.redis_repo.exists(key)
