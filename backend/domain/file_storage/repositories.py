"""
File Storage Repositories

Repository interfaces and implementations for file metadata persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from .entities import DownloadedFile


class FileRepository(ABC):
    """Abstract repository interface for file metadata persistence."""
    
    @abstractmethod
    def save(self, file: DownloadedFile) -> bool:
        """
        Save file metadata.
        
        Args:
            file: DownloadedFile to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_by_token(self, token: str) -> Optional[DownloadedFile]:
        """
        Retrieve file by token.
        
        Args:
            token: File access token
            
        Returns:
            DownloadedFile if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_by_job_id(self, job_id: str) -> Optional[DownloadedFile]:
        """
        Retrieve file by job ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            DownloadedFile if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, token: str) -> bool:
        """
        Delete file metadata.
        
        Args:
            token: File access token
            
        Returns:
            True if deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def get_expired_files(self) -> List[DownloadedFile]:
        """
        Get list of expired files.
        
        Returns:
            List of expired DownloadedFile instances
        """
        pass
    
    @abstractmethod
    def exists(self, token: str) -> bool:
        """
        Check if file metadata exists.
        
        Args:
            token: File access token
            
        Returns:
            True if exists, False otherwise
        """
        pass


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
        
        # Save token -> file metadata mapping
        token_key = f"{self.token_prefix}:{file.token}"
        if not self.redis_repo.set_json(token_key, file.to_dict(), ttl=ttl):
            return False
        
        # Save job_id -> token mapping
        job_key = f"{self.job_prefix}:{file.job_id}"
        job_data = {"token": file.token}
        return self.redis_repo.set_json(job_key, job_data, ttl=ttl)
    
    def get_by_token(self, token: str) -> Optional[DownloadedFile]:
        """Retrieve file metadata by token."""
        token_key = f"{self.token_prefix}:{token}"
        data = self.redis_repo.get_json(token_key)
        
        if data is None:
            return None
        
        try:
            file = DownloadedFile.from_dict(data)
            
            # Check if expired
            if file.is_expired():
                self.delete(token)
                return None
            
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
        Get list of expired files.
        
        Note: With Redis TTL, expired entries are automatically removed.
        This method finds files that are marked as expired but not yet removed by TTL.
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
