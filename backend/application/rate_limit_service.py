"""
Rate Limit Application Service

Application service for rate limit orchestration.
Coordinates rate limit checks across multiple limit types and manages
the interaction between domain services and infrastructure configuration.
"""

from typing import List, Optional

from domain.rate_limiting.entities import RateLimitEntity
from domain.rate_limiting.services import RateLimitManager
from domain.rate_limiting.value_objects import ClientIP, RateLimit
from infrastructure.rate_limit_config import RateLimitConfig


class RateLimitService:
    """
    Application service for rate limit orchestration.
    
    Orchestrates rate limit checks across multiple limit types (per-minute,
    per-type daily, total daily, endpoint-specific hourly) and handles
    production-only enforcement logic.
    """
    
    def __init__(
        self,
        rate_limit_manager: RateLimitManager,
        config: RateLimitConfig
    ):
        """
        Initialize with domain manager and configuration.
        
        Args:
            rate_limit_manager: Domain service for rate limiting business logic
            config: Rate limit configuration from environment
        """
        self.manager = rate_limit_manager
        self.config = config
    
    def check_download_limits(
        self,
        client_ip: str,
        video_type: str
    ) -> List[RateLimitEntity]:
        """
        Check all applicable limits for a download request.
        
        Checks three types of limits in order:
        1. Per-minute burst limit (Requirement 6)
        2. Per-video-type daily limit (Requirement 3)
        3. Total daily job limit (Requirement 4)
        
        Args:
            client_ip: Client IP address string
            video_type: Type of video (video-only, audio-only, video-audio)
        
        Returns:
            List of RateLimitEntity for all checked limits
        
        Raises:
            RateLimitExceededError: If any limit is exceeded
        """
        if not self.config.should_enforce():
            return []
        
        ip = ClientIP(client_ip)
        entities = []
        
        # Check per-minute burst limit (Requirement 6)
        entities.append(self._check_and_increment(
            ip,
            RateLimit(
                limit=self.config.batch_per_minute,
                window_seconds=60,
                limit_type='per_minute'
            )
        ))
        
        # Check per-video-type daily limit (Requirement 3)
        type_limit = self._get_video_type_limit(video_type)
        entities.append(self._check_and_increment(ip, type_limit))
        
        # Check total daily job limit (Requirement 4)
        entities.append(self._check_and_increment(
            ip,
            RateLimit(
                limit=self.config.total_jobs_daily,
                window_seconds=86400,
                limit_type='daily_total'
            )
        ))
        
        return entities
    
    def check_endpoint_limit(
        self,
        client_ip: str,
        endpoint_path: str
    ) -> Optional[RateLimitEntity]:
        """
        Check endpoint-specific hourly limit.
        
        Args:
            client_ip: Client IP address string
            endpoint_path: API endpoint path
        
        Returns:
            RateLimitEntity if limit applies, None otherwise
        
        Raises:
            RateLimitExceededError: If limit is exceeded
        """
        if not self.config.should_enforce():
            return None
        
        # Check if endpoint has specific limit (Requirement 5)
        if endpoint_path not in self.config.endpoint_hourly:
            return None
        
        ip = ClientIP(client_ip)
        limit = RateLimit(
            limit=self.config.endpoint_hourly[endpoint_path],
            window_seconds=3600,
            limit_type=f'endpoint_hourly:{endpoint_path}'
        )
        
        return self._check_and_increment(ip, limit)
    
    def get_most_restrictive_entity(
        self,
        entities: List[RateLimitEntity]
    ) -> RateLimitEntity:
        """
        Find the most restrictive limit (lowest remaining).
        
        Used for determining which headers to return when multiple
        limits apply to a single request (Requirement 10.5).
        
        Args:
            entities: List of rate limit entities to compare
        
        Returns:
            Entity with the lowest remaining count
        
        Raises:
            ValueError: If entities list is empty
        """
        if not entities:
            raise ValueError("No entities provided")
        
        return min(entities, key=lambda e: e.remaining())
    
    def _check_and_increment(
        self,
        client_ip: ClientIP,
        rate_limit: RateLimit
    ) -> RateLimitEntity:
        """
        Check limit and increment counter if not exceeded.
        
        This is a helper method that combines the check and increment
        operations to ensure atomic behavior.
        
        Args:
            client_ip: Client IP address
            rate_limit: Rate limit configuration
        
        Returns:
            Updated RateLimitEntity after increment
        
        Raises:
            RateLimitExceededError: If limit is exceeded
        """
        # Check current state (raises if exceeded)
        self.manager.check_limit(
            client_ip,
            rate_limit,
            self.config.whitelist
        )
        
        # Increment counter and return updated state
        return self.manager.increment_counter(client_ip, rate_limit)
    
    def _get_video_type_limit(self, video_type: str) -> RateLimit:
        """
        Get rate limit configuration for video type.
        
        Maps video types to their corresponding daily limits from configuration.
        Falls back to video-only limit if type is not recognized.
        
        Args:
            video_type: Type of video (video-only, audio-only, video-audio)
        
        Returns:
            RateLimit configuration for the video type
        """
        limit_map = {
            'video-only': self.config.video_only_daily,
            'audio-only': self.config.audio_only_daily,
            'video-audio': self.config.video_audio_daily
        }
        
        limit = limit_map.get(video_type, self.config.video_only_daily)
        
        return RateLimit(
            limit=limit,
            window_seconds=86400,  # 24 hours
            limit_type=f'daily_{video_type}'
        )
