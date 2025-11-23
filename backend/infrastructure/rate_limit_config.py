"""
Rate Limit Configuration

Environment-based configuration for rate limiting.
Provides centralized configuration management with sensible defaults.
"""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration from environment variables.
    
    Provides centralized configuration management for all rate limiting
    settings including feature flags, limits per video type, endpoint-specific
    limits, burst protection, and IP whitelist.
    """
    
    # Feature flags
    enabled: bool
    is_production: bool
    
    # Daily limits per video type
    video_only_daily: int
    audio_only_daily: int
    video_audio_daily: int
    total_jobs_daily: int
    
    # Endpoint-specific limits
    endpoint_hourly: Dict[str, int]
    
    # Burst protection
    batch_per_minute: int
    
    # Whitelist
    whitelist: List[str]
    
    @classmethod
    def from_env(cls) -> 'RateLimitConfig':
        """
        Load configuration from environment variables.
        
        Reads all rate limiting configuration from environment variables
        with sensible defaults for development and production environments.
        
        Returns:
            RateLimitConfig instance with loaded configuration
        """
        return cls(
            enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            is_production=os.getenv('FLASK_ENV') == 'production',
            video_only_daily=int(os.getenv('RATE_LIMIT_VIDEO_ONLY_DAILY', '20')),
            audio_only_daily=int(os.getenv('RATE_LIMIT_AUDIO_ONLY_DAILY', '20')),
            video_audio_daily=int(os.getenv('RATE_LIMIT_VIDEO_AUDIO_DAILY', '20')),
            total_jobs_daily=int(os.getenv('RATE_LIMIT_TOTAL_JOBS_DAILY', '60')),
            endpoint_hourly=cls._parse_endpoint_limits(
                os.getenv('RATE_LIMIT_ENDPOINT_HOURLY', '')
            ),
            batch_per_minute=int(os.getenv('RATE_LIMIT_BATCH_MINUTE', '10')),
            whitelist=cls._parse_whitelist(os.getenv('RATE_LIMIT_WHITELIST', ''))
        )
    
    @staticmethod
    def _parse_endpoint_limits(value: str) -> Dict[str, int]:
        """
        Parse endpoint limits from comma-separated format.
        
        Expected format: "endpoint:limit,endpoint:limit"
        Example: "/api/v1/videos/resolutions:100,/api/v1/downloads:50"
        
        Args:
            value: Comma-separated endpoint:limit pairs
        
        Returns:
            Dictionary mapping endpoint paths to hourly limits
        """
        if not value:
            return {}
        
        limits = {}
        for pair in value.split(','):
            if ':' in pair:
                endpoint, limit = pair.split(':', 1)
                limits[endpoint.strip()] = int(limit.strip())
        return limits
    
    @staticmethod
    def _parse_whitelist(value: str) -> List[str]:
        """
        Parse whitelist from comma-separated IP addresses.
        
        Expected format: "ip1,ip2,ip3"
        Example: "127.0.0.1,10.0.0.1,192.168.1.100"
        
        Args:
            value: Comma-separated IP addresses
        
        Returns:
            List of whitelisted IP addresses
        """
        if not value:
            return []
        return [ip.strip() for ip in value.split(',') if ip.strip()]
    
    def should_enforce(self) -> bool:
        """
        Determine if rate limiting should be enforced.
        
        Rate limiting is only enforced when both:
        1. RATE_LIMIT_ENABLED is true
        2. FLASK_ENV is set to "production"
        
        This ensures development and testing environments are not
        impacted by rate limits.
        
        Returns:
            True if rate limiting should be enforced, False otherwise
        """
        return self.enabled and self.is_production
