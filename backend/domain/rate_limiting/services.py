"""
Rate Limiting Domain Services

Domain service for rate limiting business logic with zero external dependencies.
"""

from datetime import datetime, timedelta
from typing import List

from .entities import RateLimitEntity
from .repositories import IRateLimitRepository
from .value_objects import ClientIP, RateLimit
from ..errors import ErrorCategory, RateLimitExceededError


class RateLimitManager:
    """
    Domain service for rate limiting business logic.
    
    Handles limit checking, counter increments, and reset time calculations.
    """
    
    def __init__(self, repository: IRateLimitRepository):
        """
        Initialize with repository interface.
        
        Args:
            repository: Rate limit repository implementation
        """
        self.repository = repository
    
    def check_limit(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit,
        whitelist: List[str]
    ) -> RateLimitEntity:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
            whitelist: List of whitelisted IPs
        
        Returns:
            RateLimitEntity with current state
        
        Raises:
            RateLimitExceededError: If limit is exceeded
        """
        # Check whitelist
        if client_ip.is_whitelisted(whitelist):
            return self._create_unlimited_entity(client_ip, rate_limit)
        
        # Get current state
        entity = self.repository.get_limit_state(client_ip, rate_limit)
        
        # Check if exceeded
        if entity.is_exceeded():
            raise RateLimitExceededError(
                category=ErrorCategory.RATE_LIMITED,
                technical_message=f"Rate limit exceeded for {client_ip.address}",
                context={
                    'limit_type': rate_limit.limit_type,
                    'limit': rate_limit.limit,
                    'reset_at': entity.reset_at.isoformat()
                }
            )
        
        return entity
    
    def increment_counter(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Increment rate limit counter atomically.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            Updated RateLimitEntity
        """
        return self.repository.increment(client_ip, rate_limit)
    
    def calculate_reset_time(
        self,
        rate_limit: RateLimit,
        current_time: datetime
    ) -> datetime:
        """
        Calculate next reset time based on limit type.
        
        For daily limits: next midnight UTC
        For hourly limits: next hour boundary
        For per-minute limits: next minute boundary
        
        Args:
            rate_limit: Rate limit configuration
            current_time: Current time
        
        Returns:
            Next reset time
        """
        if rate_limit.limit_type.startswith('daily'):
            return self._next_midnight_utc(current_time)
        elif 'hourly' in rate_limit.limit_type:
            return self._next_hour_boundary(current_time)
        else:  # per_minute or other short windows
            return self._next_minute_boundary(current_time)
    
    def _create_unlimited_entity(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Create an unlimited entity for whitelisted IPs.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            RateLimitEntity with unlimited access
        """
        reset_at = self.calculate_reset_time(rate_limit, datetime.utcnow())
        return RateLimitEntity(
            client_ip=client_ip,
            limit_type=rate_limit.limit_type,
            current_count=0,
            limit=rate_limit.limit,
            reset_at=reset_at
        )
    
    def _next_midnight_utc(self, current_time: datetime) -> datetime:
        """
        Calculate next midnight UTC.
        
        Args:
            current_time: Current time
        
        Returns:
            Next midnight UTC
        """
        tomorrow = current_time + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    
    def _next_hour_boundary(self, current_time: datetime) -> datetime:
        """
        Calculate next hour boundary.
        
        Args:
            current_time: Current time
        
        Returns:
            Next hour boundary
        """
        next_hour = current_time + timedelta(hours=1)
        return datetime(
            next_hour.year,
            next_hour.month,
            next_hour.day,
            next_hour.hour,
            0,
            0
        )
    
    def _next_minute_boundary(self, current_time: datetime) -> datetime:
        """
        Calculate next minute boundary.
        
        Args:
            current_time: Current time
        
        Returns:
            Next minute boundary
        """
        next_minute = current_time + timedelta(minutes=1)
        return datetime(
            next_minute.year,
            next_minute.month,
            next_minute.day,
            next_minute.hour,
            next_minute.minute,
            0
        )
