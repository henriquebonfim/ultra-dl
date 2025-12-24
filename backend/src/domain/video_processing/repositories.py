"""
Video Processing Repositories

Repository interfaces for video caching and metadata extraction.
Concrete implementations are in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Forward declarations to avoid circular imports
# These will be imported in implementation files
if False:  # TYPE_CHECKING equivalent
    from .entities import VideoFormat, VideoMetadata
    from .value_objects import YouTubeUrl


class IVideoMetadataExtractor(ABC):
    """
    Abstract interface for extracting video metadata and formats.

    Domain layer defines the contract, infrastructure provides implementation.
    This allows VideoProcessor to remain pure without yt-dlp dependency.

    The interface abstracts away the external video metadata extraction library
    (yt-dlp) from the domain layer, following the Dependency Inversion Principle.
    """

    @abstractmethod
    def extract_metadata(self, url: "YouTubeUrl") -> "VideoMetadata":
        """
        Extract video metadata from YouTube URL.

        Args:
            url: Validated YouTubeUrl value object

        Returns:
            VideoMetadata entity containing video information

        Raises:
            MetadataExtractionError: If extraction fails for any reason
                (network error, video unavailable, invalid video, etc.)
        """
        pass  # pragma: no cover

    @abstractmethod
    def extract_formats(self, url: "YouTubeUrl") -> List["VideoFormat"]:
        """
        Extract available formats for video.

        Args:
            url: Validated YouTubeUrl value object

        Returns:
            List of VideoFormat entities representing available download formats

        Raises:
            MetadataExtractionError: If extraction fails for any reason
                (network error, video unavailable, invalid video, etc.)
        """
        pass  # pragma: no cover


class IVideoCacheRepository(ABC):
    """
    Abstract repository interface for video metadata and format caching.

    This interface defines the contract for caching video information
    to reduce external API calls to yt-dlp. Implementations should
    handle serialization, TTL management, and cache key generation.
    """

    @abstractmethod
    def get_video_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached video metadata.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary containing video metadata if cached, None otherwise
        """
        pass  # pragma: no cover

    @abstractmethod
    def set_video_metadata(
        self, url: str, metadata: Dict[str, Any], ttl: Optional[int] = None
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
        pass  # pragma: no cover

    @abstractmethod
    def get_format_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached format information.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary containing format information if cached, None otherwise
        """
        pass  # pragma: no cover

    @abstractmethod
    def set_format_info(
        self, url: str, formats: Dict[str, Any], ttl: Optional[int] = None
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
        pass  # pragma: no cover
