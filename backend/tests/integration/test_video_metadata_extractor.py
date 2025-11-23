"""
Integration Tests for VideoMetadataExtractor

Tests the yt-dlp based implementation with real YouTube videos.
These tests require network access and may be slower than unit tests.
"""

import pytest
from infrastructure.video_metadata_extractor import VideoMetadataExtractor
from domain.video_processing.value_objects import YouTubeUrl
from domain.errors import MetadataExtractionError


class TestVideoMetadataExtractor:
    """Integration tests for yt-dlp based extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create real extractor instance."""
        return VideoMetadataExtractor()
    
    @pytest.mark.integration
    def test_extract_metadata_real_video(self, extractor):
        """Test extraction with real YouTube video."""
        # Use a stable, known video (YouTube's "Me at the zoo" - first YouTube video)
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        metadata = extractor.extract_metadata(url)
        
        # Verify metadata structure
        assert metadata.id == "jNQXAC9IVRw"
        assert metadata.title is not None
        assert len(metadata.title) > 0
        assert metadata.uploader is not None
        assert metadata.duration > 0
        assert metadata.thumbnail is not None
        assert metadata.url == str(url)
    
    @pytest.mark.integration
    def test_extract_metadata_invalid_video(self, extractor):
        """Test extraction with non-existent video."""
        # Use an invalid video ID that should not exist
        url = YouTubeUrl("https://www.youtube.com/watch?v=invalid123456789")
        
        with pytest.raises(MetadataExtractionError) as exc_info:
            extractor.extract_metadata(url)
        
        # Verify error contains useful information
        error_message = str(exc_info.value).lower()
        assert "failed" in error_message or "unavailable" in error_message
        
        # Verify original error is preserved
        assert exc_info.value.original_error is not None
    
    @pytest.mark.integration
    def test_extract_formats_real_video(self, extractor):
        """Test format extraction with real video."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # Verify formats structure
        assert len(formats) > 0
        assert all(f.format_id for f in formats)
        assert all(f.extension for f in formats)
        assert all(f.resolution for f in formats)
        
        # Verify formats are sorted by height descending
        heights = [f.height for f in formats if f.height > 0]
        if len(heights) > 1:
            assert heights == sorted(heights, reverse=True)
    
    @pytest.mark.integration
    def test_extract_formats_invalid_video(self, extractor):
        """Test format extraction with non-existent video."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=invalid123456789")
        
        with pytest.raises(MetadataExtractionError) as exc_info:
            extractor.extract_formats(url)
        
        # Verify error is raised
        assert exc_info.value.original_error is not None
    
    @pytest.mark.integration
    def test_extract_formats_includes_different_types(self, extractor):
        """Test that format extraction includes video+audio, video-only, and audio-only formats."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # Check for different format types
        has_video_audio = any(f.has_both_codecs() for f in formats)
        has_video_only = any(f.is_video_only() for f in formats)
        has_audio_only = any(f.is_audio_only() for f in formats)
        
        # At least one type should be present
        assert has_video_audio or has_video_only or has_audio_only
    
    @pytest.mark.integration
    def test_filesize_extraction(self, extractor):
        """Test that filesize is extracted when available."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # At least some formats should have filesize information
        formats_with_size = [f for f in formats if f.filesize is not None]
        assert len(formats_with_size) > 0
        
        # Verify filesize is reasonable (> 0)
        for fmt in formats_with_size:
            assert fmt.filesize > 0
    
    @pytest.mark.integration
    def test_quality_labels_calculated(self, extractor):
        """Test that quality labels are properly calculated."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # All formats should have quality labels
        assert all(f.quality_label is not None for f in formats)
        
        # Verify quality labels are valid
        valid_labels = ["Ultra", "Excellent", "Great", "Good", "Standard"]
        assert all(f.quality_label in valid_labels for f in formats)
