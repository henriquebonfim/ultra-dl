"""
Redis Rate Limit Repository Implementation

Concrete Redis-based implementation of IRateLimitRepository interface.
Provides atomic operations for distributed rate limiting with graceful degradation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import redis

from domain.rate_limiting.entities import RateLimitEntity
from domain.rate_limiting.repositories import IRateLimitRepository
from domain.rate_limiting.value_objects import ClientIP, RateLimit


logger = logging.getLogger(__name__)


class RedisRateLimitRepository(IRateLimitRepository):
    """
    Redis-based implementation of rate limit repository.
    
    Provides atomic operations using Redis INCR and EXPIREAT commands
    with graceful degradation when Redis is unavailable.
    """
    
    def __init__(self, redis_client: redis.Redis, timeout: int = 1):
        """
        Initialize with Redis client and timeout.
        
        Args:
            redis_client: Redis client instance
            timeout: Timeout for Redis operations in seconds (default: 1)
        """
        self.redis = redis_client
        self.timeout = timeout
    
    def get_limit_state(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Get current rate limit state from Redis.
        
        Retrieves the current counter value and TTL for the given client IP
        and rate limit type. If Redis is unavailable, returns an unlimited
        entity to allow the request (graceful degradation).
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            RateLimitEntity with current state
        """
        try:
            key = self._make_key(client_ip, rate_limit.limit_type)
            
            # Use pipeline for atomic operations with timeout
            pipe = self.redis.pipeline()
            pipe.socket_timeout = self.timeout
            pipe.get(key)
            pipe.ttl(key)
            results = pipe.execute()
            
            count_value = results[0]
            ttl_value = results[1]
            
            # Parse current count
            current_count = int(count_value) if count_value else 0
            
            # Calculate reset time from TTL
            if ttl_value > 0:
                reset_at = datetime.utcnow() + timedelta(seconds=ttl_value)
            else:
                # No TTL set or key doesn't exist, calculate new reset time
                reset_at = self._calculate_reset_time(rate_limit)
            
            return RateLimitEntity(
                client_ip=client_ip,
                limit_type=rate_limit.limit_type,
                current_count=current_count,
                limit=rate_limit.limit,
                reset_at=reset_at
            )
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            # Log error and return unlimited entity (graceful degradation)
            logger.error(f"Redis error in get_limit_state: {e}")
            return self._create_unlimited_entity(client_ip, rate_limit)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in get_limit_state: {e}")
            return self._create_unlimited_entity(client_ip, rate_limit)
    
    def increment(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Atomically increment counter and return updated state.
        
        Uses Redis pipeline with INCR and EXPIREAT for atomic operations.
        Sets expiration on first increment to ensure automatic cleanup.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            Updated RateLimitEntity
        """
        try:
            key = self._make_key(client_ip, rate_limit.limit_type)
            reset_time = self._calculate_reset_time(rate_limit)
            
            # Use pipeline for atomic operations with timeout
            pipe = self.redis.pipeline()
            pipe.socket_timeout = self.timeout
            
            # Increment counter
            pipe.incr(key)
            
            # Set expiration at reset time (only if not already set)
            # EXPIREAT is idempotent, so safe to call multiple times
            pipe.expireat(key, int(reset_time.timestamp()))
            
            results = pipe.execute()
            new_count = results[0]
            
            return RateLimitEntity(
                client_ip=client_ip,
                limit_type=rate_limit.limit_type,
                current_count=new_count,
                limit=rate_limit.limit,
                reset_at=reset_time
            )
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            # Log error and return unlimited entity (graceful degradation)
            logger.error(f"Redis error in increment: {e}")
            return self._create_unlimited_entity(client_ip, rate_limit)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in increment: {e}")
            return self._create_unlimited_entity(client_ip, rate_limit)
    
    def reset_counter(
        self,
        client_ip: ClientIP,
        limit_type: str
    ) -> bool:
        """
        Reset counter by deleting Redis key.
        
        Args:
            client_ip: Client IP address
            limit_type: Type of limit to reset
        
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._make_key(client_ip, limit_type)
            
            # Set timeout for delete operation
            self.redis.socket_timeout = self.timeout
            result = self.redis.delete(key)
            
            return result > 0
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis error in reset_counter: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in reset_counter: {e}")
            return False
    
    def _make_key(self, client_ip: ClientIP, limit_type: str) -> str:
        """
        Generate Redis key for rate limit counter.
        
        Format: ratelimit:{limit_type}:{ip_hash}
        Example: ratelimit:daily_video-only:a1b2c3d4e5f6g7h8
        
        Args:
            client_ip: Client IP address
            limit_type: Type of rate limit
        
        Returns:
            Redis key string
        """
        ip_hash = client_ip.hash_for_key()
        return f"ratelimit:{limit_type}:{ip_hash}"
    
    def _calculate_reset_time(self, rate_limit: RateLimit) -> datetime:
        """
        Calculate reset time based on limit type.
        
        - daily: Next midnight UTC
        - hourly: Next hour boundary
        - per_minute: Next minute boundary
        
        Args:
            rate_limit: Rate limit configuration
        
        Returns:
            DateTime when the limit resets
        """
        now = datetime.utcnow()
        
        if rate_limit.limit_type.startswith('daily') or rate_limit.limit_type == 'daily_total':
            # Next midnight UTC
            tomorrow = now + timedelta(days=1)
            return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
        elif 'hourly' in rate_limit.limit_type:
            # Next hour boundary
            next_hour = now + timedelta(hours=1)
            return datetime(next_hour.year, next_hour.month, next_hour.day, next_hour.hour, 0, 0)
        else:  # per_minute or other
            # Next minute boundary
            next_minute = now + timedelta(minutes=1)
            return datetime(next_minute.year, next_minute.month, next_minute.day,
                          next_minute.hour, next_minute.minute, 0)
    
    def _create_unlimited_entity(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Create an unlimited entity for graceful degradation.
        
        When Redis is unavailable, return an entity with zero count
        to allow the request to proceed.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            RateLimitEntity with zero count (unlimited)
        """
        return RateLimitEntity(
            client_ip=client_ip,
            limit_type=rate_limit.limit_type,
            current_count=0,
            limit=rate_limit.limit,
            reset_at=datetime.utcnow() + timedelta(seconds=rate_limit.window_seconds)
        )
