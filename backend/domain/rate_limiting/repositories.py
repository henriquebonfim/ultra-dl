"""
Rate Limiting Repositories

Repository interface for rate limit persistence.
Concrete implementations are in the infrastructure layer.
"""

from abc import ABC, abstractmethod

from .entities import RateLimitEntity
from .value_objects import ClientIP, RateLimit


class IRateLimitRepository(ABC):
    """Abstract repository interface for rate limit persistence."""
    
    @abstractmethod
    def get_limit_state(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Get current rate limit state for client.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            RateLimitEntity with current state
        """
        ...
    
    @abstractmethod
    def increment(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Atomically increment counter and return updated state.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            Updated RateLimitEntity
        """
        ...
    
    @abstractmethod
    def reset_counter(
        self,
        client_ip: ClientIP,
        limit_type: str
    ) -> bool:
        """
        Reset counter for specific limit type.
        
        Args:
            client_ip: Client IP address
            limit_type: Type of limit to reset
        
        Returns:
            True if successful
        """
        ...
