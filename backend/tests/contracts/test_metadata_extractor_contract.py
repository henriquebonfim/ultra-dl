"""
Contract Tests for IVideoMetadataExtractor

Defines the contract that all IVideoMetadataExtractor implementations must satisfy.
These tests verify that implementations correctly implement the interface.
"""

import pytest
from abc import ABC

from domain.video_processing.repositories import IVideoMetadataExtractor
from domain.video_processing.value_objects import YouTubeUrl
from domain.video_processing.entities import VideoMetadata, VideoFormat
from domain.errors import MetadataExtractionError
from infrastructure.video_metadata_extractor import VideoMetadataExtractor


class MetadataExtractorContractTest(ABC):
    """
    Contract test base class for IVideoMetadataExtractor implementations.
    
    All implementations must pass these tests to ensure they satisfy
    the interface contract defined in the domain layer.
    """
    
    @pytest.fixture
    def extractor(self) -> IVideoMetadataExtractor:
        """
        Override in subclass to provide implementation.
        
        Returns:
            IVideoMetadataExtractor implementation to test
        """
        raise NotImplementedError("Subclass must provide extractor fixture")
    
    def test_implements_interface(self, extractor):
        """Verify implementation satisfies interface."""
        assert isinstance(extractor, IVideoMetadataExtractor)
        
        # Verify required methods exist
        assert hasattr(extractor, 'extract_metadata')
        assert callable(extractor.extract_metadata)
        assert hasattr(extractor, 'extract_formats')
        assert callable(extractor.extract_formats)
    
    @pytest.mark.integration
    def test_extract_metadata_returns_metadata(self, extractor):
        """Verify extract_metadata returns VideoMetadata entity."""
        # Use a stable, known video
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        metadata = extractor.extract_metadata(url)
        
        # Verify return type
        assert isinstance(metadata, VideoMetadata)
        
        # Verify required fields are populated
        assert metadata.id is not None
        assert len(metadata.id) > 0
        assert metadata.title is not None
        assert len(metadata.title) > 0
        assert metadata.duration >= 0
        assert metadata.url is not None
    
    @pytest.mark.integration
    def test_extract_metadata_raises_on_invalid(self, extractor):
        """Verify extract_metadata raises MetadataExtractionError on failure."""
        # Use an invalid video ID
        url = YouTubeUrl("https://www.youtube.com/watch?v=invalid123456789")
        
        with pytest.raises(MetadataExtractionError):
            extractor.extract_metadata(url)
    
    @pytest.mark.integration
    def test_extract_metadata_preserves_original_error(self, extractor):
        """Verify extract_metadata preserves original error for debugging."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=invalid123456789")
        
        with pytest.raises(MetadataExtractionError) as exc_info:
            extractor.extract_metadata(url)
        
        # Verify original error is preserved
        assert exc_info.value.original_error is not None
    
    @pytest.mark.integration
    def test_extract_formats_returns_list(self, extractor):
        """Verify extract_formats returns list of VideoFormat entities."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # Verify return type
        assert isinstance(formats, list)
        assert len(formats) > 0
        
        # Verify all items are VideoFormat entities
        assert all(isinstance(f, VideoFormat) for f in formats)
        
        # Verify required fields are populated
        for fmt in formats:
            assert fmt.format_id is not None
            assert len(fmt.format_id) > 0
            assert fmt.extension is not None
            assert fmt.resolution is not None
    
    @pytest.mark.integration
    def test_extract_formats_raises_on_invalid(self, extractor):
        """Verify extract_formats raises MetadataExtractionError on failure."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=invalid123456789")
        
        with pytest.raises(MetadataExtractionError):
            extractor.extract_formats(url)
    
    @pytest.mark.integration
    def test_extract_formats_sorted_by_height(self, extractor):
        """Verify extract_formats returns formats sorted by height descending."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # Get heights of formats that have height > 0
        heights = [f.height for f in formats if f.height > 0]
        
        # Verify sorted descending (if there are multiple heights)
        if len(heights) > 1:
            assert heights == sorted(heights, reverse=True), \
                "Formats should be sorted by height in descending order"
    
    @pytest.mark.integration
    def test_extract_formats_includes_quality_labels(self, extractor):
        """Verify extract_formats includes quality labels for all formats."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        formats = extractor.extract_formats(url)
        
        # All formats should have quality labels
        assert all(f.quality_label is not None for f in formats), \
            "All formats should have quality labels"
        
        # Verify quality labels are valid
        valid_labels = ["Ultra", "Excellent", "Great", "Good", "Standard"]
        for fmt in formats:
            assert fmt.quality_label in valid_labels, \
                f"Quality label '{fmt.quality_label}' is not valid"
    
    @pytest.mark.integration
    def test_accepts_youtube_url_value_object(self, extractor):
        """Verify methods accept YouTubeUrl value object."""
        # This test verifies the interface contract accepts YouTubeUrl
        url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        
        # Should not raise TypeError
        metadata = extractor.extract_metadata(url)
        assert metadata is not None
        
        formats = extractor.extract_formats(url)
        assert formats is not None


class TestVideoMetadataExtractorContract(MetadataExtractorContractTest):
    """
    Contract tests for VideoMetadataExtractor implementation.
    
    Verifies that the yt-dlp based implementation satisfies the
    IVideoMetadataExtractor interface contract.
    """
    
    @pytest.fixture
    def extractor(self):
        """Provide VideoMetadataExtractor implementation."""
        return VideoMetadataExtractor()
