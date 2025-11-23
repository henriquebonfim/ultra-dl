"""
Rate Limiting Entities

Domain entities for rate limiting with zero external dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from .value_objects import ClientIP


@dataclass
class RateLimitEntity:
    """
    Entity representing current rate limit state for a client IP.
    
    Tracks the current count, limit, and reset time for a specific
    rate limit type (daily, hourly, per-minute).
    """
    client_ip: ClientIP
    limit_type: str
    current_count: int
    limit: int
    reset_at: datetime
    
    def is_exceeded(self) -> bool:
        """
        Check if limit is exceeded.
        
        Returns:
            True if current count has reached or exceeded the limit
        """
        return self.current_count >= self.limit
    
    def remaining(self) -> int:
        """
        Calculate remaining requests.
        
        Returns:
            Number of requests remaining (0 if limit exceeded)
        """
        return max(0, self.limit - self.current_count)
    
    def to_headers(self) -> Dict[str, str]:
        """
        Generate HTTP headers for rate limit information.
        
        Returns:
            Dictionary with X-RateLimit-* headers
        """
        return {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(self.remaining()),
            'X-RateLimit-Reset': str(int(self.reset_at.timestamp()))
        }
