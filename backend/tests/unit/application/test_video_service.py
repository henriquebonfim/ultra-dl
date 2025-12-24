"""
Unit tests for VideoService

Tests format extraction with mocked metadata extractor, caching behavior,
and error handling for unavailable videos.

Requirements: 2.1, 2.2
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.application.video_service import VideoService
from src.domain.video_processing.services import VideoProcessor
from src.domain.video_processing.repositories import IVideoCacheRepository
from src.domain.video_processing.entities import VideoMetadata
from src.domain.errors import (
    MetadataExtractionError,
    InvalidUrlError,
    VideoProcessingError,
    ErrorCategory,
)

from tests.fixtures.domain_fixtures import create_video_metadata


@pytest.fixture
def mock_video_processor():
    """Mock VideoProcessor for testing."""
    mock = Mock(spec=VideoProcessor)
    mock.validate_url.return_value = True
    mock.extract_metadata.return_value = create_video_metadata()
    mock.get_available_formats.return_value = [
        {
            "format_id": "137",
            "ext": "mp4",
            "resolution": "1920x1080",
            "height": 1080,
            "filesize": 50000000,
        },
        {
            "format_id": "140",
            "ext": "m4a",
            "resolution": "audio only",
            "height": None,
            "filesize": 5000000,
        },
    ]
    mock.formats_to_frontend_list.return_value = [
        {"format_id": "137", "quality": "1080p", "type": "video"},
        {"format_id": "140", "quality": "audio", "type": "audio"},
    ]
    return mock


@pytest.fixture
def mock_cache_service():
    """Mock cache service for testing."""
    mock = Mock(spec=IVideoCacheRepository)
    mock.get_video_metadata.return_value = None
    mock.get_format_info.return_value = None
    mock.set_video_metadata.return_value = True
    mock.set_format_info.return_value = True
    return mock


@pytest.fixture
def video_service(mock_video_processor):
    """Create VideoService without cache."""
    return VideoService(video_processor=mock_video_processor, cache_service=None)


@pytest.fixture
def video_service_with_cache(mock_video_processor, mock_cache_service):
    """Create VideoService with cache."""
    return VideoService(
        video_processor=mock_video_processor, cache_service=mock_cache_service
    )


class TestVideoServiceMetadataExtraction:
    """Test video metadata extraction."""

    def test_get_video_info_success(self, video_service, mock_video_processor):
        """
        Test successful video info retrieval.
        
        Verifies that:
        - VideoProcessor.extract_metadata is called
        - VideoProcessor.get_available_formats is called
        - Returns dictionary with meta and formats
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        
        # Act
        result = video_service.get_video_info(url)
        
        # Assert
        mock_video_processor.extract_metadata.assert_called_once_with(url)
        mock_video_processor.get_available_formats.assert_called_once_with(url)
        assert "meta" in result
        assert "formats" in result
        assert isinstance(result["meta"], dict)
        assert isinstance(result["formats"], list)

    def test_get_metadata_only_success(self, video_service, mock_video_processor):
        """
        Test successful metadata-only retrieval.
        
        Verifies that only metadata is extracted without formats.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        
        # Act
        result = video_service.get_metadata_only(url)
        
        # Assert
        mock_video_processor.extract_metadata.assert_called_once_with(url)
        mock_video_processor.get_available_formats.assert_not_called()
        assert "id" in result
        assert "title" in result
        assert "duration" in result

    def test_get_formats_only_success(self, video_service, mock_video_processor):
        """
        Test successful formats-only retrieval.
        
        Verifies that only formats are extracted without metadata.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        
        # Act
        result = video_service.get_formats_only(url)
        
        # Assert
        mock_video_processor.get_available_formats.assert_called_once_with(url)
        mock_video_processor.formats_to_frontend_list.assert_called_once()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_validate_url(self, video_service, mock_video_processor):
        """
        Test URL validation.
        
        Verifies that VideoProcessor.validate_url is called.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        
        # Act
        result = video_service.validate_url(url)
        
        # Assert
        mock_video_processor.validate_url.assert_called_once_with(url)
        assert result is True


class TestVideoServiceCaching:
    """Test caching behavior."""

    def test_get_video_info_uses_cache_when_available(
        self, video_service_with_cache, mock_video_processor, mock_cache_service
    ):
        """
        Test that cached data is used when available.
        
        Verifies that:
        - Cache is checked first
        - VideoProcessor is not called when cache hit
        - Cached data is returned
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        cached_metadata = {
            "id": "test",
            "title": "Cached Video",
            "duration": 180,
        }
        cached_formats = [{"format_id": "best", "quality": "1080p"}]
        
        mock_cache_service.get_video_metadata.return_value = cached_metadata
        mock_cache_service.get_format_info.return_value = cached_formats
        
        # Act
        result = video_service_with_cache.get_video_info(url)
        
        # Assert
        mock_cache_service.get_video_metadata.assert_called_once_with(url)
        mock_cache_service.get_format_info.assert_called_once_with(url)
        # VideoProcessor should not be called
        mock_video_processor.extract_metadata.assert_not_called()
        mock_video_processor.get_available_formats.assert_not_called()
        # Cached data should be returned
        assert result["meta"] == cached_metadata
        assert result["formats"] == cached_formats

    def test_get_video_info_caches_extracted_data(
        self, video_service_with_cache, mock_video_processor, mock_cache_service
    ):
        """
        Test that extracted data is cached.
        
        Verifies that:
        - Data is extracted when cache miss
        - Extracted data is stored in cache
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        # Cache returns None (cache miss)
        mock_cache_service.get_video_metadata.return_value = None
        mock_cache_service.get_format_info.return_value = None
        
        # Act
        result = video_service_with_cache.get_video_info(url)
        
        # Assert
        # VideoProcessor should be called
        mock_video_processor.extract_metadata.assert_called_once_with(url)
        mock_video_processor.get_available_formats.assert_called_once_with(url)
        # Data should be cached
        mock_cache_service.set_video_metadata.assert_called_once()
        mock_cache_service.set_format_info.assert_called_once()

    def test_get_metadata_only_uses_cache(
        self, video_service_with_cache, mock_video_processor, mock_cache_service
    ):
        """
        Test that metadata-only uses cache.
        
        Verifies that cached metadata is returned when available.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        cached_metadata = {"id": "test", "title": "Cached", "duration": 180}
        mock_cache_service.get_video_metadata.return_value = cached_metadata
        
        # Act
        result = video_service_with_cache.get_metadata_only(url)
        
        # Assert
        mock_video_processor.extract_metadata.assert_not_called()
        assert result == cached_metadata

    def test_get_formats_only_uses_cache(
        self, video_service_with_cache, mock_video_processor, mock_cache_service
    ):
        """
        Test that formats-only uses cache.
        
        Verifies that cached formats are returned when available.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        cached_formats = [{"format_id": "best"}]
        mock_cache_service.get_format_info.return_value = cached_formats
        
        # Act
        result = video_service_with_cache.get_formats_only(url)
        
        # Assert
        mock_video_processor.get_available_formats.assert_not_called()
        assert result == cached_formats


class TestVideoServiceErrorHandling:
    """Test error handling for video operations."""

    def test_handles_invalid_url_error(self, video_service, mock_video_processor):
        """
        Test handling of InvalidUrlError.
        
        Verifies that InvalidUrlError is propagated without wrapping.
        """
        # Arrange
        url = "https://invalid-url"
        mock_video_processor.extract_metadata.side_effect = InvalidUrlError(
            "Invalid YouTube URL"
        )
        
        # Act & Assert
        with pytest.raises(InvalidUrlError):
            video_service.get_video_info(url)

    def test_handles_metadata_extraction_error(
        self, video_service, mock_video_processor
    ):
        """
        Test handling of MetadataExtractionError.
        
        Verifies that MetadataExtractionError is propagated and
        error is categorized.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        from yt_dlp.utils import UnavailableVideoError
        
        original_error = UnavailableVideoError("Video unavailable")
        mock_video_processor.extract_metadata.side_effect = MetadataExtractionError(
            "Extraction failed", original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError):
            video_service.get_video_info(url)

    def test_handles_video_processing_error(self, video_service, mock_video_processor):
        """
        Test handling of VideoProcessingError.
        
        Verifies that VideoProcessingError is propagated.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        mock_video_processor.extract_metadata.side_effect = VideoProcessingError(
            "Processing failed"
        )
        
        # Act & Assert
        with pytest.raises(VideoProcessingError):
            video_service.get_video_info(url)

    def test_wraps_unexpected_exceptions(self, video_service, mock_video_processor):
        """
        Test that unexpected exceptions are wrapped in VideoProcessingError.
        
        Verifies that generic exceptions are caught and wrapped.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        mock_video_processor.extract_metadata.side_effect = RuntimeError(
            "Unexpected error"
        )
        
        # Act & Assert
        with pytest.raises(VideoProcessingError, match="Unexpected error"):
            video_service.get_video_info(url)


class TestVideoServiceErrorCategorization:
    """Test error categorization logic."""

    def test_categorizes_unavailable_video_error(self, video_service, mock_video_processor):
        """
        Test categorization of UnavailableVideoError.
        
        Verifies that UnavailableVideoError is categorized as
        VIDEO_UNAVAILABLE.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        from yt_dlp.utils import UnavailableVideoError
        
        original_error = UnavailableVideoError("Video unavailable")
        mock_video_processor.extract_metadata.side_effect = MetadataExtractionError(
            "Extraction failed", original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            video_service.get_video_info(url)
        
        # Verify error was categorized
        error = exc_info.value
        category = video_service._categorize_extraction_error(error)
        assert category == ErrorCategory.VIDEO_UNAVAILABLE

    def test_categorizes_extractor_error_invalid_url(
        self, video_service, mock_video_processor
    ):
        """
        Test categorization of ExtractorError with invalid URL.
        
        Verifies that ExtractorError with "unsupported url" is
        categorized as INVALID_URL.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        from yt_dlp.utils import ExtractorError
        
        original_error = ExtractorError("Unsupported URL")
        mock_video_processor.extract_metadata.side_effect = MetadataExtractionError(
            "Extraction failed", original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            video_service.get_video_info(url)
        
        # Verify error was categorized
        error = exc_info.value
        category = video_service._categorize_extraction_error(error)
        assert category == ErrorCategory.INVALID_URL

    def test_categorizes_download_error_geo_blocked(
        self, video_service, mock_video_processor
    ):
        """
        Test categorization of geo-blocked content.
        
        Verifies that errors indicating geo-blocking are
        categorized as GEO_BLOCKED.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError(
            "HTTP Error 403: This video is not available in your region"
        )
        mock_video_processor.extract_metadata.side_effect = MetadataExtractionError(
            "Extraction failed", original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            video_service.get_video_info(url)
        
        # Verify error was categorized
        error = exc_info.value
        category = video_service._categorize_extraction_error(error)
        assert category == ErrorCategory.GEO_BLOCKED

    def test_categorizes_download_error_login_required(
        self, video_service, mock_video_processor
    ):
        """
        Test categorization of login-required content.
        
        Verifies that errors indicating login requirement are
        categorized as LOGIN_REQUIRED.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError(
            "HTTP Error 403: Please sign in to view this video"
        )
        mock_video_processor.extract_metadata.side_effect = MetadataExtractionError(
            "Extraction failed", original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            video_service.get_video_info(url)
        
        # Verify error was categorized
        error = exc_info.value
        category = video_service._categorize_extraction_error(error)
        assert category == ErrorCategory.LOGIN_REQUIRED

    def test_categorizes_download_error_rate_limited(
        self, video_service, mock_video_processor
    ):
        """
        Test categorization of platform rate limiting.
        
        Verifies that 429 errors are categorized as
        PLATFORM_RATE_LIMITED.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("HTTP Error 429: Too many requests")
        mock_video_processor.extract_metadata.side_effect = MetadataExtractionError(
            "Extraction failed", original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            video_service.get_video_info(url)
        
        # Verify error was categorized
        error = exc_info.value
        category = video_service._categorize_extraction_error(error)
        assert category == ErrorCategory.PLATFORM_RATE_LIMITED

    def test_categorizes_no_original_error_as_system_error(
        self, video_service, mock_video_processor
    ):
        """
        Test categorization when no original error is present.
        
        Verifies that errors without original_error are
        categorized as SYSTEM_ERROR.
        """
        # Arrange
        error = MetadataExtractionError("Extraction failed", original_error=None)
        
        # Act
        category = video_service._categorize_extraction_error(error)
        
        # Assert
        assert category == ErrorCategory.SYSTEM_ERROR
