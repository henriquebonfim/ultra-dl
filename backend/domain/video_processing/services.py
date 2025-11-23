"""
Video Processing Services

Domain services for video metadata extraction and format processing.
"""

from typing import List, Dict, Any

from .entities import VideoMetadata, VideoFormat
from .value_objects import YouTubeUrl, InvalidUrlError, FormatType
from .repositories import IVideoMetadataExtractor
from domain.errors import VideoProcessingError, MetadataExtractionError


class VideoProcessor:
    """
    Domain service for processing YouTube videos.
    
    Handles validation and format conversion. Delegates metadata extraction
    to the injected IVideoMetadataExtractor implementation.
    """
    
    def __init__(self, metadata_extractor: IVideoMetadataExtractor):
        """
        Initialize VideoProcessor with metadata extractor dependency.
        
        Args:
            metadata_extractor: Implementation of IVideoMetadataExtractor interface
        """
        self.metadata_extractor = metadata_extractor
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is a valid YouTube URL.
        
        Args:
            url: URL string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            YouTubeUrl(url)
            return True
        except InvalidUrlError:
            return False
    
    def extract_metadata(self, url: str) -> VideoMetadata:
        """
        Extract video metadata from YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            VideoMetadata entity
            
        Raises:
            InvalidUrlError: If URL is invalid
            MetadataExtractionError: If extraction fails
        """
        # Validate URL first
        youtube_url = YouTubeUrl(url)
        
        # Delegate to metadata extractor
        return self.metadata_extractor.extract_metadata(youtube_url)
    
    def get_available_formats(self, url: str) -> List[VideoFormat]:
        """
        Get all available formats for a YouTube video.
        
        Args:
            url: YouTube URL
            
        Returns:
            List of VideoFormat entities sorted by height (descending)
            
        Raises:
            InvalidUrlError: If URL is invalid
            MetadataExtractionError: If format extraction fails
        """
        # Validate URL first
        youtube_url = YouTubeUrl(url)
        
        # Delegate to metadata extractor
        return self.metadata_extractor.extract_formats(youtube_url)
    

    
    def formats_to_frontend_list(self, formats: List[VideoFormat]) -> List[Dict[str, Any]]:
        """
        Convert VideoFormat entities to frontend-compatible format.
        
        Groups formats by type and sorts by resolution height in descending order.
        
        Args:
            formats: List of VideoFormat entities
            
        Returns:
            List of dictionaries for frontend consumption, grouped and sorted
        """
        # Convert to dictionaries
        format_dicts = [
            {
                "format_id": fmt.format_id,
                "ext": fmt.extension,
                "resolution": fmt.resolution,
                "height": fmt.height,
                "note": fmt.format_note or "",
                "filesize": fmt.filesize,
                "vcodec": fmt.video_codec,
                "acodec": fmt.audio_codec,
                "quality_label": fmt.quality_label,
                "type": fmt.format_type.value
            }
            for fmt in formats
        ]
        
        # Group by type
        video_audio = []
        video_only = []
        audio_only = []
        
        for fmt_dict in format_dicts:
            if fmt_dict["type"] == "video+audio":
                video_audio.append(fmt_dict)
            elif fmt_dict["type"] == "video_only":
                video_only.append(fmt_dict)
            elif fmt_dict["type"] == "audio_only":
                audio_only.append(fmt_dict)
        
        # Sort each group by height descending
        video_audio.sort(key=lambda x: x["height"], reverse=True)
        video_only.sort(key=lambda x: x["height"], reverse=True)
        audio_only.sort(key=lambda x: x["height"], reverse=True)
        
        # Combine groups: Video+Audio first, then Video Only, then Audio Only
        return video_audio + video_only + audio_only
