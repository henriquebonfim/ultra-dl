"""
Redis Job Repository Implementation

Concrete Redis-based implementation of JobRepository interface.
Provides atomic operations and distributed locking for job persistence.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from domain.job_management.entities import DownloadJob
from domain.job_management.repositories import JobRepository
from domain.job_management.value_objects import JobProgress, JobStatus


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

    def get_many(self, job_ids: List[str]) -> List[DownloadJob]:
        """
        Retrieve multiple jobs by their IDs using Redis pipeline.

        Uses Redis pipelining to fetch multiple jobs in a single network round trip,
        significantly improving performance when retrieving multiple jobs.

        Args:
            job_ids: List of job identifiers to retrieve

        Returns:
            List of DownloadJob instances for jobs that were found.
            Jobs that don't exist or fail to deserialize are omitted.
        """
        if not job_ids:
            return []

        try:
            # Create pipeline for batch operations
            pipeline = self.redis_repo.redis.pipeline()

            # Queue all GET operations
            keys = [self.redis_repo._make_key(f"{self.key_prefix}:{job_id}") for job_id in job_ids]
            for key in keys:
                pipeline.get(key)

            # Execute all operations in one round trip
            results = pipeline.execute()

            # Deserialize results
            jobs = []
            for result in results:
                if result is not None:
                    try:
                        import json
                        data = json.loads(result.decode('utf-8') if isinstance(result, bytes) else result)
                        job = DownloadJob.from_dict(data)
                        jobs.append(job)
                    except Exception as e:
                        print(f"Error deserializing job in batch get: {e}")
                        continue

            return jobs

        except Exception as e:
            print(f"Error in get_many operation: {e}")
            return []

    def save_many(self, jobs: List[DownloadJob]) -> bool:
        """
        Save or update multiple jobs using Redis pipeline for atomic operation.

        Uses Redis pipelining to save multiple jobs atomically in a single
        network round trip, ensuring all jobs are saved or none are.

        Args:
            jobs: List of DownloadJob instances to save

        Returns:
            True if all jobs were successfully saved, False if any save failed
        """
        if not jobs:
            return True

        try:
            # Create pipeline for atomic batch operations
            pipeline = self.redis_repo.redis.pipeline()

            # Queue all SET operations
            for job in jobs:
                key = self.redis_repo._make_key(f"{self.key_prefix}:{job.job_id}")
                data = job.to_dict()

                import json
                json_data = json.dumps(data)

                # Set with TTL
                pipeline.setex(key, self.ttl, json_data)

            # Execute all operations atomically
            results = pipeline.execute()

            # Check if all operations succeeded
            return all(results)

        except Exception as e:
            print(f"Error in save_many operation: {e}")
            return False

    def find_by_status(self, status: JobStatus, limit: int = 100) -> List[DownloadJob]:
        """
        Find jobs by their current status using Redis SCAN.

        Uses Redis SCAN command to iterate through job keys without blocking,
        then filters by status. This is more efficient than KEYS for large datasets.

        Args:
            status: The JobStatus to filter by
            limit: Maximum number of jobs to return (default: 100)

        Returns:
            List of DownloadJob instances matching the status criteria
        """
        try:
            matching_jobs = []
            pattern = self.redis_repo._make_key(f"{self.key_prefix}:*")

            # Use SCAN to iterate through keys without blocking Redis
            cursor = 0
            while True:
                cursor, keys = self.redis_repo.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100  # Hint for number of keys to return per iteration
                )

                # Fetch jobs in batch using pipeline
                if keys:
                    pipeline = self.redis_repo.redis.pipeline()
                    for key in keys:
                        pipeline.get(key)

                    results = pipeline.execute()

                    # Filter by status
                    for result in results:
                        if result is not None:
                            try:
                                import json
                                data = json.loads(result.decode('utf-8') if isinstance(result, bytes) else result)
                                job = DownloadJob.from_dict(data)

                                if job.status == status:
                                    matching_jobs.append(job)

                                    # Stop if we've reached the limit
                                    if len(matching_jobs) >= limit:
                                        return matching_jobs

                            except Exception as e:
                                print(f"Error deserializing job in find_by_status: {e}")
                                continue

                # SCAN returns 0 when iteration is complete
                if cursor == 0:
                    break

            return matching_jobs

        except Exception as e:
            print(f"Error in find_by_status operation: {e}")
            return []
