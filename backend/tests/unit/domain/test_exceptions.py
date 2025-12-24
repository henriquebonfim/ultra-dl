"""
Unit tests for domain exceptions.

Tests verify domain exception behavior including:
- All domain exceptions inherit from DomainError
- Exception messages are descriptive
- Exception wraps original_error when provided

Requirements: 1.4, 14.1
"""

import pytest
from src.domain.errors import (
    DomainError,
    MetadataExtractionError,
    FormatNotFoundError,
    VideoProcessingError,
    InvalidUrlError,
)
from src.domain.job_management.services import JobNotFoundError, JobStateError
from src.domain.video_processing.value_objects import InvalidFormatIdError
from src.domain.file_storage.value_objects import InvalidDownloadTokenError


class TestDomainExceptions:
    """Test domain exception hierarchy and behavior."""
    
    def test_all_domain_exceptions_inherit_from_domain_error(self):
        """
        Test that all domain exceptions inherit from DomainError.
        
        Verifies the exception hierarchy is correctly established.
        """
        # Test base domain exceptions
        assert issubclass(MetadataExtractionError, DomainError)
        assert issubclass(FormatNotFoundError, DomainError)
        assert issubclass(VideoProcessingError, DomainError)
        assert issubclass(InvalidUrlError, DomainError)
        
        # Test job management exceptions
        assert issubclass(JobNotFoundError, DomainError)
        assert issubclass(JobStateError, DomainError)
        
        # Test value object exceptions
        assert issubclass(InvalidFormatIdError, DomainError)
        assert issubclass(InvalidDownloadTokenError, DomainError)
    
    def test_domain_error_has_descriptive_message(self):
        """
        Test that DomainError exceptions have descriptive messages.
        """
        message = "This is a descriptive error message"
        error = DomainError(message)
        
        assert str(error) == message
        assert error.args[0] == message
    
    def test_metadata_extraction_error_has_descriptive_message(self):
        """
        Test that MetadataExtractionError has descriptive message.
        """
        message = "Failed to extract video metadata"
        error = MetadataExtractionError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_format_not_found_error_has_descriptive_message(self):
        """
        Test that FormatNotFoundError has descriptive message.
        """
        message = "Format 137 not found for video"
        error = FormatNotFoundError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_video_processing_error_has_descriptive_message(self):
        """
        Test that VideoProcessingError has descriptive message.
        """
        message = "Video processing failed"
        error = VideoProcessingError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_invalid_url_error_has_descriptive_message(self):
        """
        Test that InvalidUrlError has descriptive message.
        """
        message = "Invalid YouTube URL: not-a-url"
        error = InvalidUrlError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_job_not_found_error_has_descriptive_message(self):
        """
        Test that JobNotFoundError has descriptive message.
        """
        message = "Job abc123 not found"
        error = JobNotFoundError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_job_state_error_has_descriptive_message(self):
        """
        Test that JobStateError has descriptive message.
        """
        message = "Cannot start job in completed state"
        error = JobStateError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_invalid_format_id_error_has_descriptive_message(self):
        """
        Test that InvalidFormatIdError has descriptive message.
        """
        message = "Invalid format ID: invalid@format"
        error = InvalidFormatIdError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_invalid_download_token_error_has_descriptive_message(self):
        """
        Test that InvalidDownloadTokenError has descriptive message.
        """
        message = "Invalid download token: must be at least 32 characters"
        error = InvalidDownloadTokenError(message)
        
        assert str(error) == message
        assert isinstance(error, DomainError)
    
    def test_domain_error_wraps_original_error(self):
        """
        Test that DomainError can wrap an original exception.
        
        Verifies that original_error attribute is set when provided.
        """
        original = ValueError("Original error")
        message = "Domain error wrapping original"
        error = DomainError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, ValueError)
    
    def test_metadata_extraction_error_wraps_original_error(self):
        """
        Test that MetadataExtractionError can wrap an original exception.
        """
        original = ConnectionError("Network timeout")
        message = "Failed to extract metadata"
        error = MetadataExtractionError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, ConnectionError)
    
    def test_format_not_found_error_wraps_original_error(self):
        """
        Test that FormatNotFoundError can wrap an original exception.
        """
        original = KeyError("format_id")
        message = "Format not found"
        error = FormatNotFoundError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, KeyError)
    
    def test_video_processing_error_wraps_original_error(self):
        """
        Test that VideoProcessingError can wrap an original exception.
        """
        original = RuntimeError("Processing failed")
        message = "Video processing error"
        error = VideoProcessingError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, RuntimeError)
    
    def test_invalid_url_error_wraps_original_error(self):
        """
        Test that InvalidUrlError can wrap an original exception.
        """
        original = ValueError("Invalid URL format")
        message = "Invalid YouTube URL"
        error = InvalidUrlError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, ValueError)
    
    def test_job_not_found_error_wraps_original_error(self):
        """
        Test that JobNotFoundError can wrap an original exception.
        """
        original = KeyError("job_id")
        message = "Job not found"
        error = JobNotFoundError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, KeyError)
    
    def test_job_state_error_wraps_original_error(self):
        """
        Test that JobStateError can wrap an original exception.
        """
        original = ValueError("Invalid state transition")
        message = "Cannot transition job state"
        error = JobStateError(message, original_error=original)
        
        assert str(error) == message
        assert error.original_error == original
        assert isinstance(error.original_error, ValueError)
    
    def test_domain_error_without_original_error(self):
        """
        Test that DomainError works without original_error.
        
        Verifies that original_error is None when not provided.
        """
        message = "Domain error without original"
        error = DomainError(message)
        
        assert str(error) == message
        assert error.original_error is None
    
    def test_exception_can_be_raised_and_caught(self):
        """
        Test that domain exceptions can be raised and caught.
        """
        with pytest.raises(DomainError) as exc_info:
            raise DomainError("Test error")
        
        assert "Test error" in str(exc_info.value)
    
    def test_specific_exception_can_be_caught_as_domain_error(self):
        """
        Test that specific domain exceptions can be caught as DomainError.
        
        Verifies polymorphic exception handling.
        """
        with pytest.raises(DomainError) as exc_info:
            raise JobNotFoundError("Job not found")
        
        assert "Job not found" in str(exc_info.value)
        assert isinstance(exc_info.value, JobNotFoundError)
        assert isinstance(exc_info.value, DomainError)
    
    def test_exception_preserves_traceback(self):
        """
        Test that exceptions preserve traceback information.
        """
        try:
            raise MetadataExtractionError("Extraction failed")
        except MetadataExtractionError as e:
            assert e.__traceback__ is not None
    
    def test_exception_with_original_preserves_both_messages(self):
        """
        Test that wrapping an exception preserves both messages.
        """
        original = ValueError("Original message")
        wrapper = DomainError("Wrapper message", original_error=original)
        
        assert str(wrapper) == "Wrapper message"
        assert str(wrapper.original_error) == "Original message"
    
    def test_all_exceptions_are_instances_of_exception(self):
        """
        Test that all domain exceptions are instances of base Exception.
        """
        exceptions = [
            DomainError("test"),
            MetadataExtractionError("test"),
            FormatNotFoundError("test"),
            VideoProcessingError("test"),
            InvalidUrlError("test"),
            JobNotFoundError("test"),
            JobStateError("test"),
            InvalidFormatIdError("test"),
            InvalidDownloadTokenError("test"),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, Exception)
            assert isinstance(exc, DomainError)
