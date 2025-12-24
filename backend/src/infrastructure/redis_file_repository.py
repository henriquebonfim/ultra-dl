"""
Redis File Repository Implementation

Concrete Redis-based implementation of FileRepository interface.
Stores file metadata with automatic expiration using Redis TTL.
"""

from typing import List, Optional

from src.domain.file_storage.entities import DownloadedFile
from src.domain.file_storage.repositories import FileRepository


class RedisFileRepository(FileRepository):
    """
    Redis-based implementation of FileRepository.

    Stores file metadata with automatic expiration using Redis TTL.
    """

    def __init__(self, redis_repository):
        """
        Initialize with Redis repository.

        Args:
            redis_repository: RedisRepository instance from infrastructure layer
        """
        self.redis_repo = redis_repository
        self.token_prefix = "file_token"
        self.job_prefix = "file_job"

    def save(self, file: DownloadedFile) -> bool:
        """
        Save file metadata to Redis with TTL.

        Creates two mappings:
        - token -> file metadata
        - job_id -> token (for lookup by job)
        """
        # Calculate TTL in seconds
        ttl = file.get_remaining_seconds()
        if ttl <= 0:
            return False  # Don't save expired files

        # Add grace period to Redis TTL to allow proper 410 responses
        # Redis TTL should be longer than file expiration to let the app
        # detect expiration and return 410 instead of 404
        redis_ttl = ttl + 60  # Keep in Redis for 1 minute after expiration

        # Save token -> file metadata mapping
        token_key = f"{self.token_prefix}:{file.token}"
        if not self.redis_repo.set_json(token_key, file.to_dict(), ttl=redis_ttl):
            return False

        # Save job_id -> token mapping
        job_key = f"{self.job_prefix}:{file.job_id}"
        job_data = {"token": str(file.token)}
        return self.redis_repo.set_json(job_key, job_data, ttl=redis_ttl)

    def get_by_token(self, token: str) -> Optional[DownloadedFile]:
        """
        Retrieve file metadata by token.
        
        This method returns metadata even during the grace period (60 seconds after
        file expiration) to enable proper 410 Gone responses. During the grace period,
        the metadata exists in Redis but the physical file has been deleted from storage.
        
        Returns:
            DownloadedFile if metadata exists, None if not found in Redis
        """
        token_key = f"{self.token_prefix}:{token}"
        data = self.redis_repo.get_json(token_key)

        if data is None:
            return None

        try:
            file = DownloadedFile.from_dict(data)
            return file
        except Exception as e:
            print(f"Error deserializing file metadata for token {token}: {e}")
            return None

    def get_by_job_id(self, job_id: str) -> Optional[DownloadedFile]:
        """Retrieve file metadata by job ID."""
        job_key = f"{self.job_prefix}:{job_id}"
        data = self.redis_repo.get_json(job_key)

        if data is None:
            return None

        token = data.get("token")
        if not token:
            return None

        return self.get_by_token(token)

    def delete(self, token: str) -> bool:
        """
        Delete file metadata from Redis.

        Removes both token and job_id mappings.
        """
        # Get file to find job_id
        file = self.get_by_token(token)

        # Delete token mapping
        token_key = f"{self.token_prefix}:{token}"
        token_deleted = self.redis_repo.delete(token_key)

        # Delete job mapping if file was found
        if file:
            job_key = f"{self.job_prefix}:{file.job_id}"
            self.redis_repo.delete(job_key)

        return token_deleted

    def get_expired_files(self) -> List[DownloadedFile]:
        """
        Get list of expired files for proactive cleanup.
        
        This method identifies files that have passed their expiration time but still
        have metadata in Redis (within the 60-second grace period). It enables proactive
        cleanup to delete both physical files and metadata, preventing resource leaks.
        
        Physical files are deleted at expiration time, but metadata is retained for an
        additional 60 seconds to support 410 Gone responses for recently expired files.
        
        Returns:
            List of DownloadedFile objects that are expired but still in Redis
        """

        pattern = f"{self.token_prefix}:*"
        keys = self.redis_repo.get_keys_by_pattern(pattern)

        expired_files = []
        for key in keys:
            token = key.replace(f"{self.token_prefix}:", "")
            file = self.get_by_token(token)

            if file and file.is_expired():
                expired_files.append(file)

        return expired_files

    def exists(self, token: str) -> bool:
        """Check if file metadata exists in Redis."""
        token_key = f"{self.token_prefix}:{token}"
        return self.redis_repo.exists(token_key)
