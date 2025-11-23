"""
Redis Cache Service Implementation

Concrete Redis-based implementation of IVideoCacheRepository interface.
Provides caching for video metadata and format information with TTL support.
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from domain.video_processing.repositories import IVideoCacheRepository


logger = logging.getLogger(__name__)


class RedisCacheService(IVideoCacheRepository):
    """
    Redis-based implementation of video cache repository.
    
    Uses SHA-256 URL hashing for cache keys to prevent injection attacks
    and handle long URLs. Implements TTL-based expiration and structured
    logging for cache hit/miss events.
    """
    
    def __init__(self, redis_repository, default_ttl: int = 300):
        """
        Initialize Redis cache service.
        
        Args:
            redis_repository: RedisRepository instance from infrastructure layer
            default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.redis_repo = redis_repository
        self.default_ttl = default_ttl
        self.metadata_prefix = "video:metadata"
        self.formats_prefix = "video:formats"
    
    def _hash_url(self, url: str) -> str:
        """
        Generate SHA-256 hash of URL for cache key.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    def _make_metadata_key(self, url: str) -> str:
        """
        Generate cache key for video metadata.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Cache key in format: video:metadata:{url_hash}
        """
        url_hash = self._hash_url(url)
        return f"{self.metadata_prefix}:{url_hash}"
    
    def _make_formats_key(self, url: str) -> str:
        """
        Generate cache key for format information.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Cache key in format: video:formats:{url_hash}
        """
        url_hash = self._hash_url(url)
        return f"{self.formats_prefix}:{url_hash}"
    
    def get_video_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached video metadata.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing video metadata if cached, None otherwise
        """
        key = self._make_metadata_key(url)
        
        try:
            data = self.redis_repo.get_json(key)
            
            if data is not None:
                logger.debug(f"Cache hit for metadata: {key}")
                return data
            else:
                logger.debug(f"Cache miss for metadata: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached metadata for {key}: {e}")
            return None
    
    def set_video_metadata(
        self, 
        url: str, 
        metadata: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache video metadata with TTL.
        
        Args:
            url: YouTube video URL
            metadata: Video metadata dictionary to cache
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        key = self._make_metadata_key(url)
        cache_ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            success = self.redis_repo.set_json(key, metadata, ttl=cache_ttl)
            
            if success:
                logger.debug(f"Cached metadata: {key} (TTL: {cache_ttl}s)")
            else:
                logger.warning(f"Failed to cache metadata: {key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching metadata for {key}: {e}")
            return False
    
    def get_format_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached format information.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing format information if cached, None otherwise
        """
        key = self._make_formats_key(url)
        
        try:
            data = self.redis_repo.get_json(key)
            
            if data is not None:
                logger.debug(f"Cache hit for formats: {key}")
                return data
            else:
                logger.debug(f"Cache miss for formats: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached formats for {key}: {e}")
            return None
    
    def set_format_info(
        self, 
        url: str, 
        formats: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache format information with TTL.
        
        Args:
            url: YouTube video URL
            formats: Format information dictionary to cache
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        key = self._make_formats_key(url)
        cache_ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            success = self.redis_repo.set_json(key, formats, ttl=cache_ttl)
            
            if success:
                logger.debug(f"Cached formats: {key} (TTL: {cache_ttl}s)")
            else:
                logger.warning(f"Failed to cache formats: {key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching formats for {key}: {e}")
            return False
