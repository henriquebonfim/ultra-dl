"""
Video Application Service

Coordinates video processing use cases.
"""

import logging
from typing import Any, Dict, List, Optional

from src.domain.errors import ErrorCategory, MetadataExtractionError
from src.domain.video_processing import (
    InvalidUrlError,
    IVideoCacheRepository,
    VideoProcessingError,
    VideoProcessor,
)

logger = logging.getLogger(__name__)


class VideoService:
    """
    Application service for video processing operations.

    Coordinates video metadata extraction and format retrieval.
    Integrates caching to reduce external yt-dlp calls.
    Publishes domain events for metadata extraction failures.
    """

    def __init__(
        self,
        video_processor: VideoProcessor,
        cache_service: Optional[IVideoCacheRepository] = None,
    ):
        """
        Initialize VideoService with domain services.

        Args:
            video_processor: VideoProcessor instance (required)
            cache_service: Optional cache service for video metadata and formats
        """
        self.video_processor = video_processor
        self.cache_service = cache_service

    def _categorize_extraction_error(
        self, error: MetadataExtractionError
    ) -> ErrorCategory:
        """
        Categorize metadata extraction errors into error categories.

        This is an application-layer concern that maps infrastructure errors
        (wrapped in MetadataExtractionError) to user-friendly error categories.

        Args:
            error: MetadataExtractionError that may wrap original yt-dlp exception

        Returns:
            ErrorCategory enum value representing the error type
        """
        # If no original error, return generic system error
        if error.original_error is None:
            return ErrorCategory.SYSTEM_ERROR

        # Import yt-dlp exceptions locally to avoid hard dependency
        try:
            from yt_dlp.utils import (
                DownloadError,
                ExtractorError,
                UnavailableVideoError,
            )
        except ImportError:
            logger.warning("yt-dlp not available for error categorization")
            return ErrorCategory.SYSTEM_ERROR

        exception = error.original_error
        error_str = str(exception).lower()

        # Check for specific yt-dlp exception types
        if isinstance(exception, UnavailableVideoError):
            return ErrorCategory.VIDEO_UNAVAILABLE

        if isinstance(exception, ExtractorError):
            if "unsupported url" in error_str or "invalid url" in error_str:
                return ErrorCategory.INVALID_URL
            elif "private video" in error_str or "members-only" in error_str:
                return ErrorCategory.VIDEO_UNAVAILABLE
            elif "this video is not available" in error_str:
                return ErrorCategory.VIDEO_UNAVAILABLE
            else:
                return ErrorCategory.DOWNLOAD_FAILED

        if isinstance(exception, DownloadError):
            # Analyze download error message
            if "http error 404" in error_str or "not found" in error_str:
                return ErrorCategory.VIDEO_UNAVAILABLE
            elif "http error 403" in error_str or "forbidden" in error_str:
                # Check for geo-blocking indicators
                if (
                    "geo" in error_str
                    or "region" in error_str
                    or "location" in error_str
                ):
                    return ErrorCategory.GEO_BLOCKED
                # Check for login requirements
                elif (
                    "login" in error_str
                    or "sign in" in error_str
                    or "authenticate" in error_str
                ):
                    return ErrorCategory.LOGIN_REQUIRED
                else:
                    return ErrorCategory.VIDEO_UNAVAILABLE
            elif "http error 429" in error_str or "too many requests" in error_str:
                return ErrorCategory.PLATFORM_RATE_LIMITED
            elif "format" in error_str and (
                "not available" in error_str or "not found" in error_str
            ):
                return ErrorCategory.FORMAT_NOT_SUPPORTED
            elif (
                "network" in error_str
                or "connection" in error_str
                or "timeout" in error_str
            ):
                return ErrorCategory.NETWORK_ERROR
            else:
                return ErrorCategory.DOWNLOAD_FAILED

        # Check error message content for common patterns
        if "url" in error_str and (
            "invalid" in error_str or "unsupported" in error_str
        ):
            return ErrorCategory.INVALID_URL
        elif (
            "unavailable" in error_str
            or "private" in error_str
            or "deleted" in error_str
        ):
            return ErrorCategory.VIDEO_UNAVAILABLE
        elif "format" in error_str and "not" in error_str:
            return ErrorCategory.FORMAT_NOT_SUPPORTED
        elif "too large" in error_str or "file size" in error_str:
            return ErrorCategory.FILE_TOO_LARGE
        elif (
            "network" in error_str
            or "connection" in error_str
            or "timeout" in error_str
        ):
            return ErrorCategory.NETWORK_ERROR
        elif "rate limit" in error_str or "too many" in error_str:
            return ErrorCategory.PLATFORM_RATE_LIMITED
        elif "geo" in error_str or "region" in error_str or "location" in error_str:
            return ErrorCategory.GEO_BLOCKED
        elif (
            "login" in error_str
            or "sign in" in error_str
            or "authenticate" in error_str
        ):
            return ErrorCategory.LOGIN_REQUIRED
        else:
            return ErrorCategory.SYSTEM_ERROR

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video metadata and available formats.

        Catches domain exceptions, categorizes them, and publishes
        MetadataExtractionFailedEvent on errors.

        Args:
            url: YouTube URL

        Returns:
            Dictionary with metadata and formats

        Raises:
            InvalidUrlError: If URL is invalid
            MetadataExtractionError: If extraction fails (with categorized error)
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Fetching video info for URL: {url}")

            # Try to get from cache if cache service is available
            cached_metadata = None
            cached_formats = None

            if self.cache_service:
                cached_metadata = self.cache_service.get_video_metadata(url)
                cached_formats = self.cache_service.get_format_info(url)

            # If both are cached, return cached data
            if cached_metadata and cached_formats:
                logger.info(f"Returning cached video info for URL: {url}")
                return {"meta": cached_metadata, "formats": cached_formats}

            # Extract metadata (from cache or yt-dlp)
            if cached_metadata:
                metadata_dict = cached_metadata
                logger.debug("Using cached metadata")
            else:
                metadata = self.video_processor.extract_metadata(url)
                metadata_dict = {
                    "id": metadata.id,
                    "title": metadata.title,
                    "uploader": metadata.uploader,
                    "duration": metadata.duration,
                    "thumbnail": metadata.thumbnail,
                }
                # Cache metadata
                if self.cache_service:
                    self.cache_service.set_video_metadata(url, metadata_dict)

            # Get available formats (from cache or yt-dlp)
            if cached_formats:
                formats_list = cached_formats
                logger.debug("Using cached formats")
            else:
                formats = self.video_processor.get_available_formats(url)
                formats_list = self.video_processor.formats_to_frontend_list(formats)
                # Cache formats
                if self.cache_service:
                    self.cache_service.set_format_info(url, formats_list)

            logger.info(
                f"Successfully fetched {len(formats_list)} formats for video: {metadata_dict['title']}"
            )

            return {"meta": metadata_dict, "formats": formats_list}
        except InvalidUrlError:
            logger.warning(f"Invalid URL provided: {url}")
            raise
        except MetadataExtractionError as e:
            # Categorize the error
            error_category = self._categorize_extraction_error(e)
            logger.error(
                f"Metadata extraction failed for URL {url}: {error_category.value}"
            )

            # Re-raise with categorized error
            raise
        except VideoProcessingError as e:
            logger.error(f"Video processing error for URL {url}: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching video info for URL {url}")
            raise VideoProcessingError(f"Unexpected error: {str(e)}")

    def validate_url(self, url: str) -> bool:
        """
        Validate YouTube URL.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        return self.video_processor.validate_url(url)

    def get_metadata_only(self, url: str) -> Dict[str, Any]:
        """
        Get only video metadata without formats.

        Catches domain exceptions, categorizes them, and publishes
        MetadataExtractionFailedEvent on errors.

        Args:
            url: YouTube URL

        Returns:
            Dictionary with metadata

        Raises:
            InvalidUrlError: If URL is invalid
            MetadataExtractionError: If extraction fails
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Fetching metadata for URL: {url}")

            # Try to get from cache if cache service is available
            if self.cache_service:
                cached_metadata = self.cache_service.get_video_metadata(url)
                if cached_metadata:
                    logger.info(f"Returning cached metadata for URL: {url}")
                    return cached_metadata

            # Extract from yt-dlp
            metadata = self.video_processor.extract_metadata(url)

            metadata_dict = {
                "id": metadata.id,
                "title": metadata.title,
                "uploader": metadata.uploader,
                "duration": metadata.duration,
                "thumbnail": metadata.thumbnail,
            }

            # Cache metadata
            if self.cache_service:
                self.cache_service.set_video_metadata(url, metadata_dict)

            return metadata_dict
        except InvalidUrlError:
            logger.warning(f"Invalid URL provided: {url}")
            raise
        except MetadataExtractionError as e:
            # Categorize the error
            error_category = self._categorize_extraction_error(e)
            logger.error(
                f"Metadata extraction failed for URL {url}: {error_category.value}"
            )
            raise
        except Exception as e:
            logger.error(f"Error fetching metadata for URL {url}: {str(e)}")
            raise VideoProcessingError(f"Unexpected error: {str(e)}")

    def get_formats_only(self, url: str) -> List[Dict[str, Any]]:
        """
        Get only available formats without metadata.

        Catches domain exceptions, categorizes them, and publishes
        MetadataExtractionFailedEvent on errors.

        Args:
            url: YouTube URL

        Returns:
            List of format dictionaries

        Raises:
            InvalidUrlError: If URL is invalid
            MetadataExtractionError: If extraction fails
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Fetching formats for URL: {url}")

            # Try to get from cache if cache service is available
            if self.cache_service:
                cached_formats = self.cache_service.get_format_info(url)
                if cached_formats:
                    logger.info(f"Returning cached formats for URL: {url}")
                    return cached_formats

            # Extract from yt-dlp
            formats = self.video_processor.get_available_formats(url)
            formats_list = self.video_processor.formats_to_frontend_list(formats)

            # Cache formats
            if self.cache_service:
                self.cache_service.set_format_info(url, formats_list)

            logger.info(f"Successfully fetched {len(formats_list)} formats")

            return formats_list
        except InvalidUrlError:
            logger.warning(f"Invalid URL provided: {url}")
            raise
        except MetadataExtractionError as e:
            # Categorize the error
            error_category = self._categorize_extraction_error(e)
            logger.error(
                f"Format extraction failed for URL {url}: {error_category.value}"
            )
            raise
        except Exception as e:
            logger.error(f"Error fetching formats for URL {url}: {str(e)}")
            raise VideoProcessingError(f"Unexpected error: {str(e)}")
