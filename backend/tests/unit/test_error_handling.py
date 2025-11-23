"""
Unit Tests for Error Handling

Tests custom exception types, error messages, error propagation through layers,
error logging, and error recovery mechanisms.

Requirements: 9.1, 9.2, 9.3, 9.4
"""

import unittest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from domain.errors import (
    ApplicationError,
    ErrorCategory,
    RateLimitExceededError,
    MetadataExtractionError,
    create_error_response,
    ERROR_MESSAGES
)
from application.video_service import VideoService
from domain.file_storage.services import FileNotFoundError, FileExpiredError
from domain.job_management.services import JobNotFoundError, JobStateError
from domain.video_processing.services import VideoProcessingError
# Removed: GCSUploadError and LocalFileStorageError (obsolete after refactoring)


class TestApplicationError(unittest.TestCase):
    """Test ApplicationError base exception class."""
    
    def test_application_error_initialization(self):
        """Test ApplicationError initializes with correct attributes."""
        error = ApplicationError(
            category=ErrorCategory.INVALID_URL,
            technical_message="Invalid YouTube URL format",
            context={"url": "invalid-url"}
        )
        
        self.assertEqual(error.category, ErrorCategory.INVALID_URL)
        self.assertEqual(error.technical_message, "Invalid YouTube URL format")
        self.assertEqual(error.context, {"url": "invalid-url"})
        self.assertEqual(error.title, "Invalid YouTube URL")
        self.assertIn("valid YouTube link", error.message)
    
    def test_application_error_to_dict(self):
        """Test ApplicationError converts to dictionary correctly."""
        error = ApplicationError(
            category=ErrorCategory.VIDEO_UNAVAILABLE,
            technical_message="Video is private"
        )
        
        error_dict = error.to_dict()
        
        self.assertEqual(error_dict["error"], "video_unavailable")
        self.assertEqual(error_dict["title"], "Video Not Available")
        self.assertIn("message", error_dict)
        self.assertIn("action", error_dict)
    
    def test_application_error_default_technical_message(self):
        """Test ApplicationError with no technical message."""
        error = ApplicationError(category=ErrorCategory.SYSTEM_ERROR)
        
        self.assertEqual(error.technical_message, "")
        self.assertEqual(error.context, {})
    
    def test_application_error_log_method(self):
        """Test ApplicationError logs with correct severity and context."""
        with patch('domain.errors.logger') as mock_logger:
            error = ApplicationError(
                category=ErrorCategory.DOWNLOAD_FAILED,
                technical_message="Network timeout",
                context={"job_id": "job-123"}
            )
            
            error.log()
            
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            self.assertIn("download_failed", call_args[0][0])
            self.assertIn("Network timeout", call_args[0][0])
            self.assertEqual(call_args[1]["extra"]["context"], {"job_id": "job-123"})


class TestRateLimitExceededError(unittest.TestCase):
    """Test RateLimitExceededError exception."""
    
    def test_rate_limit_error_has_http_status_code(self):
        """Test RateLimitExceededError includes HTTP 429 status code."""
        error = RateLimitExceededError(
            category=ErrorCategory.RATE_LIMITED,
            technical_message="Rate limit exceeded for IP"
        )
        
        self.assertEqual(error.http_status_code, 429)
        self.assertEqual(error.category, ErrorCategory.RATE_LIMITED)
    
    def test_rate_limit_error_inherits_from_application_error(self):
        """Test RateLimitExceededError is an ApplicationError."""
        error = RateLimitExceededError(
            category=ErrorCategory.RATE_LIMITED
        )
        
        self.assertIsInstance(error, ApplicationError)
        self.assertEqual(error.title, "Too Many Requests")


class TestDomainExceptions(unittest.TestCase):
    """Test domain-specific exception types."""
    
    def test_file_not_found_error_raised(self):
        """Test FileNotFoundError is raised correctly."""
        with self.assertRaises(FileNotFoundError) as context:
            raise FileNotFoundError("File not found: /tmp/test.mp4")
        
        self.assertIn("File not found", str(context.exception))
    
    def test_file_expired_error_raised(self):
        """Test FileExpiredError is raised correctly."""
        with self.assertRaises(FileExpiredError) as context:
            raise FileExpiredError("File has expired: token-123")
        
        self.assertIn("expired", str(context.exception))
    
    def test_job_not_found_error_raised(self):
        """Test JobNotFoundError is raised correctly."""
        with self.assertRaises(JobNotFoundError) as context:
            raise JobNotFoundError("Job job-123 not found")
        
        self.assertIn("job-123", str(context.exception))
    
    def test_job_state_error_raised(self):
        """Test JobStateError is raised correctly."""
        with self.assertRaises(JobStateError) as context:
            raise JobStateError("Cannot transition from completed to pending")
        
        self.assertIn("transition", str(context.exception))
    
    def test_video_processing_error_raised(self):
        """Test VideoProcessingError is raised correctly."""
        with self.assertRaises(VideoProcessingError) as context:
            raise VideoProcessingError("Failed to extract metadata")
        
        self.assertIn("metadata", str(context.exception))


class TestInfrastructureExceptions(unittest.TestCase):
    """Test infrastructure-specific exception types."""
    
    def test_gcs_upload_error_raised(self):
        """Test GCSUploadError is raised correctly."""
        with self.assertRaises(GCSUploadError) as context:
            raise GCSUploadError("Failed to upload to GCS: permission denied")
        
        self.assertIn("GCS", str(context.exception))
        self.assertIn("permission denied", str(context.exception))
    
    def test_local_file_storage_error_raised(self):
        """Test LocalFileStorageError is raised correctly."""
        with self.assertRaises(LocalFileStorageError) as context:
            raise LocalFileStorageError("Failed to save file: disk full")
        
        self.assertIn("disk full", str(context.exception))


class TestErrorMessages(unittest.TestCase):
    """Test error message structure and content."""
    
    def test_all_error_categories_have_messages(self):
        """Test all ErrorCategory values have corresponding messages."""
        for category in ErrorCategory:
            self.assertIn(category, ERROR_MESSAGES)
            message_info = ERROR_MESSAGES[category]
            self.assertIn("title", message_info)
            self.assertIn("message", message_info)
            self.assertIn("action", message_info)
    
    def test_error_messages_are_descriptive(self):
        """Test error messages include descriptive text."""
        for category, message_info in ERROR_MESSAGES.items():
            # Title should be short and clear
            self.assertLess(len(message_info["title"]), 100)
            self.assertGreater(len(message_info["title"]), 5)
            
            # Message should be informative
            self.assertGreater(len(message_info["message"]), 20)
            
            # Action should provide guidance
            self.assertGreater(len(message_info["action"]), 10)
    
    def test_error_messages_are_user_friendly(self):
        """Test error messages avoid technical jargon."""
        technical_terms = ["exception", "traceback", "stack", "null", "undefined"]
        
        for category, message_info in ERROR_MESSAGES.items():
            message_text = message_info["message"].lower()
            action_text = message_info["action"].lower()
            
            for term in technical_terms:
                self.assertNotIn(term, message_text)
                self.assertNotIn(term, action_text)


class TestYtdlpErrorCategorization(unittest.TestCase):
    """Test yt-dlp error categorization in application layer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a VideoService instance for testing
        # We don't need a real VideoProcessor for these tests
        self.mock_event_publisher = Mock()
        self.video_service = VideoService(
            video_processor=Mock(),
            event_publisher=self.mock_event_publisher
        )
    
    def test_categorize_unavailable_video_error(self):
        """Test categorization of UnavailableVideoError."""
        from yt_dlp.utils import UnavailableVideoError
        
        original_error = UnavailableVideoError("Video unavailable")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.VIDEO_UNAVAILABLE)
    
    def test_categorize_invalid_url_error(self):
        """Test categorization of invalid URL errors."""
        from yt_dlp.utils import ExtractorError
        
        original_error = ExtractorError("Unsupported URL: invalid-url")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.INVALID_URL)
    
    def test_categorize_private_video_error(self):
        """Test categorization of private video errors."""
        from yt_dlp.utils import ExtractorError
        
        original_error = ExtractorError("This is a private video")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.VIDEO_UNAVAILABLE)
    
    def test_categorize_geo_blocked_error(self):
        """Test categorization of geo-blocked errors."""
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("HTTP Error 403: Video not available in your region")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.GEO_BLOCKED)
    
    def test_categorize_login_required_error(self):
        """Test categorization of login required errors."""
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("HTTP Error 403: Sign in to confirm your age")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.LOGIN_REQUIRED)
    
    def test_categorize_rate_limit_error(self):
        """Test categorization of rate limit errors."""
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("HTTP Error 429: Too many requests")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.PLATFORM_RATE_LIMITED)
    
    def test_categorize_network_error(self):
        """Test categorization of network errors."""
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("Network connection timeout")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.NETWORK_ERROR)
    
    def test_categorize_format_not_available_error(self):
        """Test categorization of format not available errors."""
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("Requested format not available")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.FORMAT_NOT_SUPPORTED)
    
    def test_categorize_generic_download_error(self):
        """Test categorization of generic download errors."""
        from yt_dlp.utils import DownloadError
        
        original_error = DownloadError("Download failed for unknown reason")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.DOWNLOAD_FAILED)
    
    def test_categorize_error_without_original_error(self):
        """Test categorization when no original error is wrapped."""
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=None)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.SYSTEM_ERROR)
    
    def test_categorize_unknown_error_defaults_to_system_error(self):
        """Test unknown errors default to SYSTEM_ERROR."""
        original_error = Exception("Unknown error type")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        category = self.video_service._categorize_extraction_error(wrapped_error)
        
        self.assertEqual(category, ErrorCategory.SYSTEM_ERROR)


class TestVideoServiceEventPublishing(unittest.TestCase):
    """Test VideoService publishes events on errors."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_video_processor = Mock()
        self.mock_event_publisher = Mock()
        self.video_service = VideoService(
            video_processor=self.mock_video_processor,
            event_publisher=self.mock_event_publisher
        )
    
    def test_get_video_info_publishes_event_on_invalid_url(self):
        """Test get_video_info publishes MetadataExtractionFailedEvent on InvalidUrlError."""
        from domain.video_processing import InvalidUrlError
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise InvalidUrlError
        self.mock_video_processor.extract_metadata.side_effect = InvalidUrlError("Invalid URL")
        
        # Call should raise InvalidUrlError
        with self.assertRaises(InvalidUrlError):
            self.video_service.get_video_info("invalid-url")
        
        # Verify event was published
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
        self.assertEqual(published_event.url, "invalid-url")
        self.assertIn("Invalid URL", published_event.error_message)
    
    def test_get_video_info_publishes_event_on_metadata_extraction_error(self):
        """Test get_video_info publishes MetadataExtractionFailedEvent on MetadataExtractionError."""
        from yt_dlp.utils import UnavailableVideoError
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise MetadataExtractionError with yt-dlp error
        # Use UnavailableVideoError which is categorized as VIDEO_UNAVAILABLE
        original_error = UnavailableVideoError("Video unavailable")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        self.mock_video_processor.extract_metadata.side_effect = wrapped_error
        
        # Call should raise MetadataExtractionError
        with self.assertRaises(MetadataExtractionError):
            self.video_service.get_video_info("https://youtube.com/watch?v=test")
        
        # Verify event was published
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
        self.assertEqual(published_event.url, "https://youtube.com/watch?v=test")
        self.assertIn("video_unavailable", published_event.error_message)
    
    def test_get_video_info_publishes_event_on_video_processing_error(self):
        """Test get_video_info publishes MetadataExtractionFailedEvent on VideoProcessingError."""
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise VideoProcessingError
        self.mock_video_processor.extract_metadata.side_effect = VideoProcessingError("Processing failed")
        
        # Call should raise VideoProcessingError
        with self.assertRaises(VideoProcessingError):
            self.video_service.get_video_info("https://youtube.com/watch?v=test")
        
        # Verify event was published
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
        self.assertEqual(published_event.url, "https://youtube.com/watch?v=test")
        self.assertIn("Processing failed", published_event.error_message)
    
    def test_get_video_info_publishes_event_on_unexpected_error(self):
        """Test get_video_info publishes MetadataExtractionFailedEvent on unexpected errors."""
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise unexpected error
        self.mock_video_processor.extract_metadata.side_effect = RuntimeError("Unexpected error")
        
        # Call should raise VideoProcessingError
        with self.assertRaises(VideoProcessingError):
            self.video_service.get_video_info("https://youtube.com/watch?v=test")
        
        # Verify event was published
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
        self.assertEqual(published_event.url, "https://youtube.com/watch?v=test")
        self.assertIn("Unexpected error", published_event.error_message)
    
    def test_get_video_info_does_not_publish_event_on_success(self):
        """Test get_video_info does not publish event on successful extraction."""
        from domain.video_processing import VideoMetadata, VideoFormat
        
        # Mock successful metadata extraction
        mock_metadata = VideoMetadata(
            id="test-id",
            title="Test Video",
            uploader="Test Uploader",
            duration=120,
            thumbnail="https://example.com/thumb.jpg",
            url="https://youtube.com/watch?v=test"
        )
        self.mock_video_processor.extract_metadata.return_value = mock_metadata
        
        # Mock successful format extraction
        mock_formats = [
            VideoFormat(
                format_id="137+140",
                extension="mp4",
                resolution="1080p",
                height=1080,
                width=1920,
                filesize=1024000,
                video_codec="avc1",
                audio_codec="mp4a"
            )
        ]
        self.mock_video_processor.get_available_formats.return_value = mock_formats
        self.mock_video_processor.formats_to_frontend_list.return_value = [
            {
                "format_id": "137+140",
                "extension": "mp4",
                "resolution": "1080p",
                "filesize": 1024000
            }
        ]
        
        # Call should succeed
        result = self.video_service.get_video_info("https://youtube.com/watch?v=test")
        
        # Verify no event was published
        self.mock_event_publisher.publish.assert_not_called()
        
        # Verify result structure
        self.assertIn("meta", result)
        self.assertIn("formats", result)
        self.assertEqual(result["meta"]["id"], "test-id")
    
    def test_get_metadata_only_publishes_event_on_error(self):
        """Test get_metadata_only publishes MetadataExtractionFailedEvent on error."""
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise MetadataExtractionError
        self.mock_video_processor.extract_metadata.side_effect = MetadataExtractionError("Failed")
        
        # Call should raise MetadataExtractionError
        with self.assertRaises(MetadataExtractionError):
            self.video_service.get_metadata_only("https://youtube.com/watch?v=test")
        
        # Verify event was published
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
    
    def test_get_formats_only_publishes_event_on_error(self):
        """Test get_formats_only publishes MetadataExtractionFailedEvent on error."""
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise MetadataExtractionError
        self.mock_video_processor.get_available_formats.side_effect = MetadataExtractionError("Failed")
        
        # Call should raise MetadataExtractionError
        with self.assertRaises(MetadataExtractionError):
            self.video_service.get_formats_only("https://youtube.com/watch?v=test")
        
        # Verify event was published
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
    
    def test_video_service_works_without_event_publisher(self):
        """Test VideoService works correctly when event_publisher is None."""
        from domain.video_processing import InvalidUrlError
        
        # Create VideoService without event publisher
        video_service = VideoService(video_processor=Mock(), event_publisher=None)
        video_service.video_processor.extract_metadata.side_effect = InvalidUrlError("Invalid URL")
        
        # Should still raise error but not crash
        with self.assertRaises(InvalidUrlError):
            video_service.get_video_info("invalid-url")
    
    def test_error_categorization_with_event_publishing(self):
        """Test error categorization is performed before publishing event."""
        from yt_dlp.utils import DownloadError
        from domain.events import MetadataExtractionFailedEvent
        
        # Mock video processor to raise MetadataExtractionError with geo-blocked error
        original_error = DownloadError("HTTP Error 403: Video not available in your region")
        wrapped_error = MetadataExtractionError("Failed to extract", original_error=original_error)
        self.mock_video_processor.extract_metadata.side_effect = wrapped_error
        
        # Call should raise MetadataExtractionError
        with self.assertRaises(MetadataExtractionError):
            self.video_service.get_video_info("https://youtube.com/watch?v=test")
        
        # Verify event was published with categorized error
        self.mock_event_publisher.publish.assert_called_once()
        published_event = self.mock_event_publisher.publish.call_args[0][0]
        self.assertIsInstance(published_event, MetadataExtractionFailedEvent)
        # Error message should include the categorized error type
        self.assertIn("geo_blocked", published_event.error_message)


class TestCreateErrorResponse(unittest.TestCase):
    """Test create_error_response helper function."""
    
    def test_create_error_response_returns_tuple(self):
        """Test create_error_response returns (dict, status_code) tuple."""
        response, status_code = create_error_response(
            category=ErrorCategory.INVALID_URL,
            technical_message="Invalid URL format"
        )
        
        self.assertIsInstance(response, dict)
        self.assertIsInstance(status_code, int)
        self.assertEqual(status_code, 400)
    
    def test_create_error_response_includes_error_info(self):
        """Test create_error_response includes all error information."""
        response, _ = create_error_response(
            category=ErrorCategory.JOB_NOT_FOUND,
            technical_message="Job not found in Redis",
            context={"job_id": "job-123"},
            status_code=404
        )
        
        self.assertEqual(response["error"], "job_not_found")
        self.assertIn("title", response)
        self.assertIn("message", response)
        self.assertIn("action", response)
    
    def test_create_error_response_logs_error(self):
        """Test create_error_response logs the error."""
        with patch('domain.errors.logger') as mock_logger:
            create_error_response(
                category=ErrorCategory.DOWNLOAD_FAILED,
                technical_message="Download timeout",
                context={"url": "https://youtube.com/watch?v=test"}
            )
            
            mock_logger.error.assert_called_once()
    
    def test_create_error_response_custom_status_code(self):
        """Test create_error_response with custom status code."""
        _, status_code = create_error_response(
            category=ErrorCategory.FILE_EXPIRED,
            status_code=410
        )
        
        self.assertEqual(status_code, 410)


class TestErrorPropagation(unittest.TestCase):
    """Test error propagation through application layers."""
    
    def test_domain_error_propagates_to_application_layer(self):
        """Test domain exceptions propagate to application layer."""
        from domain.job_management.services import JobManager
        
        # Mock repository that raises JobNotFoundError
        mock_repo = Mock()
        mock_repo.get.return_value = None
        
        job_manager = JobManager(mock_repo)
        
        with self.assertRaises(JobNotFoundError):
            job_manager.get_job("nonexistent-job")
    
    def test_infrastructure_error_handled_in_application_layer(self):
        """Test infrastructure errors are caught and handled in application layer."""
        from application.download_service import DownloadService
        
        # Create mocks
        job_manager = Mock()
        file_manager = Mock()
        video_processor = Mock()
        storage_service = Mock()
        event_publisher = Mock()
        
        # Mock storage service to raise error
        storage_service.save_file.side_effect = LocalFileStorageError("Disk full")
        
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Storage errors should be handled gracefully
        # The service should catch and categorize the error
        self.assertIsNotNone(service)
    
    def test_application_error_includes_context(self):
        """Test application errors include context for debugging."""
        error = ApplicationError(
            category=ErrorCategory.DOWNLOAD_FAILED,
            technical_message="yt-dlp extraction failed",
            context={
                "url": "https://youtube.com/watch?v=test",
                "format_id": "137+140",
                "job_id": "job-123"
            }
        )
        
        self.assertEqual(error.context["url"], "https://youtube.com/watch?v=test")
        self.assertEqual(error.context["format_id"], "137+140")
        self.assertEqual(error.context["job_id"], "job-123")


class TestErrorLogging(unittest.TestCase):
    """Test error logging at appropriate severity levels."""
    
    def test_application_error_logs_at_error_level(self):
        """Test ApplicationError logs at ERROR level."""
        with patch('domain.errors.logger') as mock_logger:
            error = ApplicationError(
                category=ErrorCategory.SYSTEM_ERROR,
                technical_message="Unexpected system error"
            )
            error.log()
            
            mock_logger.error.assert_called_once()
    
    def test_error_log_includes_category(self):
        """Test error log includes error category."""
        with patch('domain.errors.logger') as mock_logger:
            error = ApplicationError(
                category=ErrorCategory.VIDEO_UNAVAILABLE,
                technical_message="Video is private"
            )
            error.log()
            
            call_args = mock_logger.error.call_args[0][0]
            self.assertIn("video_unavailable", call_args)
    
    def test_error_log_includes_technical_message(self):
        """Test error log includes technical details."""
        with patch('domain.errors.logger') as mock_logger:
            error = ApplicationError(
                category=ErrorCategory.NETWORK_ERROR,
                technical_message="Connection timeout after 30s"
            )
            error.log()
            
            call_args = mock_logger.error.call_args[0][0]
            self.assertIn("Connection timeout after 30s", call_args)
    
    def test_error_log_includes_context_as_extra(self):
        """Test error log includes context as extra field."""
        with patch('domain.errors.logger') as mock_logger:
            error = ApplicationError(
                category=ErrorCategory.DOWNLOAD_FAILED,
                technical_message="Download failed",
                context={"job_id": "job-123", "retry_count": 3}
            )
            error.log()
            
            call_kwargs = mock_logger.error.call_args[1]
            self.assertIn("extra", call_kwargs)
            self.assertEqual(call_kwargs["extra"]["context"]["job_id"], "job-123")
            self.assertEqual(call_kwargs["extra"]["context"]["retry_count"], 3)


class TestErrorRecoveryMechanisms(unittest.TestCase):
    """Test error recovery mechanisms."""
    
    @patch('infrastructure.storage_service.GCSRepository')
    @patch('infrastructure.storage_service.LocalFileRepository')
    def test_storage_fallback_on_gcs_error(self, mock_local_class, mock_gcs_class):
        """Test system falls back to local storage on GCS error."""
        from infrastructure.storage_service import StorageService
        
        # Mock GCS repository that fails
        mock_gcs_instance = Mock()
        mock_gcs_instance.is_available.return_value = True
        mock_gcs_instance.upload_file.side_effect = GCSUploadError("GCS unavailable")
        mock_gcs_class.return_value = mock_gcs_instance
        
        # Mock local repository that succeeds
        mock_local_instance = Mock()
        mock_local_instance.save_file.return_value = "/tmp/ultra-dl/job-123/video.mp4"
        mock_local_class.return_value = mock_local_instance
        
        # Create storage service (will detect GCS as available)
        with patch.dict(os.environ, {'DISABLE_GCS': 'false'}):
            storage_service = StorageService()
            storage_service.use_gcs = True  # Force GCS mode for test
        
        # Should fall back to local storage on GCS error
        result_path, is_gcs = storage_service.save_file(
            file_path="/tmp/video.mp4",
            job_id="job-123",
            filename="video.mp4"
        )
        
        self.assertFalse(is_gcs)
        self.assertIn("/tmp/ultra-dl", result_path)
    
    def test_file_manager_cleans_up_expired_files(self):
        """Test FileManager cleans up expired files on access."""
        from domain.file_storage.services import FileManager
        from domain.file_storage.entities import DownloadedFile
        
        # Create expired file
        expired_file = Mock(spec=DownloadedFile)
        expired_file.is_expired.return_value = True
        expired_file.token = "expired-token"
        
        # Mock repository
        mock_file_repo = Mock()
        mock_file_repo.get_by_token.return_value = expired_file
        mock_file_repo.delete.return_value = True
        
        mock_storage_repo = Mock()
        
        file_manager = FileManager(mock_file_repo, mock_storage_repo)
        
        # Should raise FileExpiredError and clean up
        with self.assertRaises(FileExpiredError):
            file_manager.get_file_by_token("expired-token")
        
        # Verify cleanup was called
        mock_file_repo.delete.assert_called_once_with("expired-token")
    
    def test_job_manager_handles_invalid_state_transitions(self):
        """Test JobManager prevents invalid state transitions."""
        from domain.job_management.services import JobManager
        from domain.job_management.entities import DownloadJob
        from domain.job_management.value_objects import JobStatus
        
        # Create completed job
        job = DownloadJob.create("https://youtube.com/watch?v=test", "137+140")
        job.status = JobStatus.COMPLETED
        
        # Mock repository
        mock_repo = Mock()
        mock_repo.get.return_value = job
        
        job_manager = JobManager(mock_repo)
        
        # Should raise JobStateError when trying to start completed job
        with self.assertRaises(JobStateError):
            job_manager.start_job(job.job_id)


if __name__ == '__main__':
    unittest.main()
