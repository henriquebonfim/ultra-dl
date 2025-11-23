"""
Rate Limiting Value Objects

Immutable value objects for rate limiting with zero external dependencies.
"""

import hashlib
import ipaddress
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ClientIP:
    """
    Immutable client IP address value object.
    
    Validates IP address format and provides whitelist checking
    and hash generation for Redis keys.
    """
    address: str
    
    def __post_init__(self):
        """Validate IP address format (IPv4 or IPv6)."""
        try:
            # This will raise ValueError if invalid
            ipaddress.ip_address(self.address)
        except ValueError as e:
            raise ValueError(f"Invalid IP address format: {self.address}") from e
    
    def is_whitelisted(self, whitelist: List[str]) -> bool:
        """
        Check if IP is in whitelist.
        
        Args:
            whitelist: List of whitelisted IP addresses
        
        Returns:
            True if IP is whitelisted, False otherwise
        """
        return self.address in whitelist
    
    def hash_for_key(self) -> str:
        """
        Generate Redis key-safe hash.
        
        Hashes the IP address for privacy while maintaining uniqueness.
        Truncates to 16 characters to balance collision risk with key length.
        
        Returns:
            16-character hexadecimal hash
        """
        return hashlib.sha256(self.address.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class RateLimit:
    """
    Immutable rate limit configuration value object.
    
    Defines the limit, time window, and type for rate limiting.
    """
    limit: int
    window_seconds: int
    limit_type: str
    
    def __post_init__(self):
        """Validate limit values."""
        if self.limit <= 0:
            raise ValueError(f"Limit must be positive, got {self.limit}")
        if self.window_seconds <= 0:
            raise ValueError(f"Window must be positive, got {self.window_seconds}")
        if not self.limit_type:
            raise ValueError("Limit type is required")
