"""
Unit tests for VideoProcessor domain service.

Tests VideoProcessor with mocked IVideoMetadataExtractor to ensure
domain layer remains pure without external dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock

from domain.video_processing.services import VideoProcessor
from domain.video_processing.repositories import IVideoMetadataExtractor
from domain.video_processing.entities import VideoMetadata, VideoFormat
from domain.video_processing.value_objects import YouTubeUrl, InvalidUrlError, FormatType
from domain.errors import MetadataExtractionError


class TestVideoProcessor:
    """Test VideoProcessor with mocked metadata extractor."""
    
    @pytest.fixture
    def mock_extractor(self):
        """Create mock metadata extractor."""
        return Mock(spec=IVideoMetadataExtractor)
    
    @pytest.fixture
    def processor(self, mock_extractor):
        """Create VideoProcessor with mock."""
        return VideoProcessor(mock_extractor)
    
    # URL Validation Tests
    
    def test_validate_url_valid_youtube_url(self, processor):
        """Test URL validation with valid YouTube URL."""
        assert processor.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    
    def test_validate_url_valid_short_url(self, processor):
        """Test URL validation with valid YouTube short URL."""
        assert processor.validate_url("https://youtu.be/dQw4w9WgXcQ") is True
    
    def test_validate_url_invalid_url(self, processor):
        """Test URL validation with invalid URL."""
        assert processor.validate_url("not-a-url") is False
    
    def test_validate_url_non_youtube_url(self, processor):
        """Test URL validation with non-YouTube URL."""
        assert processor.validate_url("https://www.example.com/video") is False
    
    def test_validate_url_empty_string(self, processor):
        """Test URL validation with empty string."""
        assert processor.validate_url("") is False
    
    # Metadata Extraction Tests
    
    def test_extract_metadata_success(self, processor, mock_extractor):
        """Test successful metadata extraction."""
        # Arrange
        expected_metadata = VideoMetadata(
            id="test123",
            title="Test Video",
            uploader="Test Channel",
            duration=180,
            thumbnail="https://example.com/thumb.jpg",
            url="https://www.youtube.com/watch?v=test123"
        )
        mock_extractor.extract_metadata.return_value = expected_metadata
        
        # Act
        result = processor.extract_metadata("https://www.youtube.com/watch?v=test123")
        
        # Assert
        assert result == expected_metadata
        assert result.id == "test123"
        assert result.title == "Test Video"
        assert result.duration == 180
        mock_extractor.extract_metadata.assert_called_once()
        
        # Verify YouTubeUrl was passed to extractor
        call_args = mock_extractor.extract_metadata.call_args[0]
        assert isinstance(call_args[0], YouTubeUrl)
    
    def test_extract_metadata_invalid_url(self, processor, mock_extractor):
        """Test metadata extraction with invalid URL."""
        # Act & Assert
        with pytest.raises(InvalidUrlError):
            processor.extract_metadata("invalid-url")
        
        # Extractor should not be called
        mock_extractor.extract_metadata.assert_not_called()
    
    def test_extract_metadata_extraction_error(self, processor, mock_extractor):
        """Test metadata extraction when extractor fails."""
        # Arrange
        mock_extractor.extract_metadata.side_effect = MetadataExtractionError(
            "Failed to extract metadata"
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            processor.extract_metadata("https://www.youtube.com/watch?v=test123")
        
        assert "Failed to extract metadata" in str(exc_info.value)
        mock_extractor.extract_metadata.assert_called_once()
    
    def test_extract_metadata_with_original_error(self, processor, mock_extractor):
        """Test metadata extraction error with original error attached."""
        # Arrange
        original_error = Exception("Network timeout")
        mock_extractor.extract_metadata.side_effect = MetadataExtractionError(
            "Failed to extract metadata",
            original_error=original_error
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            processor.extract_metadata("https://www.youtube.com/watch?v=test123")
        
        assert exc_info.value.original_error == original_error
    
    # Format Extraction Tests
    
    def test_get_available_formats_success(self, processor, mock_extractor):
        """Test successful format extraction."""
        # Arrange
        expected_formats = [
            VideoFormat(
                format_id="137",
                extension="mp4",
                resolution="1920x1080",
                height=1080,
                width=1920,
                filesize=50000000,
                video_codec="avc1",
                audio_codec="mp4a",
                quality_label="1080p",
                format_note="Premium"
            ),
            VideoFormat(
                format_id="136",
                extension="mp4",
                resolution="1280x720",
                height=720,
                width=1280,
                filesize=30000000,
                video_codec="avc1",
                audio_codec="mp4a",
                quality_label="720p",
                format_note="HD"
            )
        ]
        mock_extractor.extract_formats.return_value = expected_formats
        
        # Act
        result = processor.get_available_formats("https://www.youtube.com/watch?v=test123")
        
        # Assert
        assert len(result) == 2
        assert result[0].format_id == "137"
        assert result[0].height == 1080
        assert result[1].format_id == "136"
        assert result[1].height == 720
        mock_extractor.extract_formats.assert_called_once()
        
        # Verify YouTubeUrl was passed to extractor
        call_args = mock_extractor.extract_formats.call_args[0]
        assert isinstance(call_args[0], YouTubeUrl)
    
    def test_get_available_formats_invalid_url(self, processor, mock_extractor):
        """Test format extraction with invalid URL."""
        # Act & Assert
        with pytest.raises(InvalidUrlError):
            processor.get_available_formats("invalid-url")
        
        # Extractor should not be called
        mock_extractor.extract_formats.assert_not_called()
    
    def test_get_available_formats_extraction_error(self, processor, mock_extractor):
        """Test format extraction when extractor fails."""
        # Arrange
        mock_extractor.extract_formats.side_effect = MetadataExtractionError(
            "Failed to extract formats"
        )
        
        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc_info:
            processor.get_available_formats("https://www.youtube.com/watch?v=test123")
        
        assert "Failed to extract formats" in str(exc_info.value)
        mock_extractor.extract_formats.assert_called_once()
    
    def test_get_available_formats_empty_list(self, processor, mock_extractor):
        """Test format extraction returns empty list."""
        # Arrange
        mock_extractor.extract_formats.return_value = []
        
        # Act
        result = processor.get_available_formats("https://www.youtube.com/watch?v=test123")
        
        # Assert
        assert result == []
        assert len(result) == 0
    
    # Frontend Format Conversion Tests
    
    def test_formats_to_frontend_list_mixed_formats(self, processor):
        """Test conversion of mixed format types to frontend list."""
        # Arrange
        formats = [
            VideoFormat(
                format_id="22",
                extension="mp4",
                resolution="1280x720",
                height=720,
                width=1280,
                filesize=30000000,
                video_codec="avc1",
                audio_codec="mp4a",
                quality_label="720p",
                format_note="HD"
            ),
            VideoFormat(
                format_id="137",
                extension="mp4",
                resolution="1920x1080",
                height=1080,
                width=1920,
                filesize=50000000,
                video_codec="avc1",
                audio_codec="none",
                quality_label="1080p",
                format_note="Video only"
            ),
            VideoFormat(
                format_id="140",
                extension="m4a",
                resolution="audio only",
                height=0,
                width=None,
                filesize=5000000,
                video_codec="none",
                audio_codec="mp4a",
                quality_label="128kbps",
                format_note="Audio only"
            )
        ]
        
        # Act
        result = processor.formats_to_frontend_list(formats)
        
        # Assert
        assert len(result) == 3
        
        # Verify grouping: video+audio first, then video_only, then audio_only
        assert result[0]["format_id"] == "22"
        assert result[0]["type"] == "video+audio"
        assert result[1]["format_id"] == "137"
        assert result[1]["type"] == "video_only"
        assert result[2]["format_id"] == "140"
        assert result[2]["type"] == "audio_only"
        
        # Verify all required fields are present
        for fmt in result:
            assert "format_id" in fmt
            assert "ext" in fmt
            assert "resolution" in fmt
            assert "height" in fmt
            assert "filesize" in fmt
            assert "vcodec" in fmt
            assert "acodec" in fmt
            assert "quality_label" in fmt
            assert "type" in fmt
    
    def test_formats_to_frontend_list_sorting_within_groups(self, processor):
        """Test that formats are sorted by height within each group."""
        # Arrange
        formats = [
            VideoFormat(
                format_id="18",
                extension="mp4",
                resolution="640x360",
                height=360,
                width=640,
                filesize=10000000,
                video_codec="avc1",
                audio_codec="mp4a",
                quality_label="360p",
                format_note="SD"
            ),
            VideoFormat(
                format_id="22",
                extension="mp4",
                resolution="1280x720",
                height=720,
                width=1280,
                filesize=30000000,
                video_codec="avc1",
                audio_codec="mp4a",
                quality_label="720p",
                format_note="HD"
            ),
            VideoFormat(
                format_id="37",
                extension="mp4",
                resolution="1920x1080",
                height=1080,
                width=1920,
                filesize=50000000,
                video_codec="avc1",
                audio_codec="mp4a",
                quality_label="1080p",
                format_note="Full HD"
            )
        ]
        
        # Act
        result = processor.formats_to_frontend_list(formats)
        
        # Assert - should be sorted by height descending
        assert result[0]["height"] == 1080
        assert result[1]["height"] == 720
        assert result[2]["height"] == 360
    
    def test_formats_to_frontend_list_empty_list(self, processor):
        """Test conversion of empty format list."""
        # Act
        result = processor.formats_to_frontend_list([])
        
        # Assert
        assert result == []
        assert len(result) == 0
    
    def test_formats_to_frontend_list_audio_only_formats(self, processor):
        """Test conversion of audio-only formats."""
        # Arrange
        formats = [
            VideoFormat(
                format_id="140",
                extension="m4a",
                resolution="audio only",
                height=0,
                width=None,
                filesize=5000000,
                video_codec="none",
                audio_codec="mp4a",
                quality_label="128kbps",
                format_note="Medium quality"
            ),
            VideoFormat(
                format_id="251",
                extension="webm",
                resolution="audio only",
                height=0,
                width=None,
                filesize=7000000,
                video_codec="none",
                audio_codec="opus",
                quality_label="160kbps",
                format_note="High quality"
            )
        ]
        
        # Act
        result = processor.formats_to_frontend_list(formats)
        
        # Assert
        assert len(result) == 2
        assert all(fmt["type"] == "audio_only" for fmt in result)
        assert all(fmt["height"] == 0 for fmt in result)
    
    # Integration Tests (with real YouTubeUrl validation)
    
    def test_extract_metadata_validates_url_before_calling_extractor(self, processor, mock_extractor):
        """Test that URL validation happens before calling extractor."""
        # Arrange
        mock_extractor.extract_metadata.return_value = VideoMetadata(
            id="test",
            title="Test",
            uploader="Test",
            duration=100,
            thumbnail="",
            url="https://www.youtube.com/watch?v=test"
        )
        
        # Act - valid URL
        processor.extract_metadata("https://www.youtube.com/watch?v=test")
        
        # Assert - extractor was called
        assert mock_extractor.extract_metadata.call_count == 1
        
        # Act - invalid URL
        with pytest.raises(InvalidUrlError):
            processor.extract_metadata("invalid")
        
        # Assert - extractor was not called again
        assert mock_extractor.extract_metadata.call_count == 1
    
    def test_get_available_formats_validates_url_before_calling_extractor(self, processor, mock_extractor):
        """Test that URL validation happens before calling extractor."""
        # Arrange
        mock_extractor.extract_formats.return_value = []
        
        # Act - valid URL
        processor.get_available_formats("https://www.youtube.com/watch?v=test")
        
        # Assert - extractor was called
        assert mock_extractor.extract_formats.call_count == 1
        
        # Act - invalid URL
        with pytest.raises(InvalidUrlError):
            processor.get_available_formats("invalid")
        
        # Assert - extractor was not called again
        assert mock_extractor.extract_formats.call_count == 1
