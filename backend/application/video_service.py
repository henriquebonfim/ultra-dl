"""
Video Application Service

Coordinates video processing use cases.
"""

from typing import Dict, Any, List
import logging

from domain.video_processing import (
    VideoProcessor, 
    VideoMetadata, 
    VideoFormat,
    InvalidUrlError,
    VideoProcessingError
)


logger = logging.getLogger(__name__)


class VideoService:
    """
    Application service for video processing operations.
    
    Coordinates video metadata extraction and format retrieval.
    """
    
    def __init__(self):
        """Initialize VideoService with domain services."""
        self.video_processor = VideoProcessor()
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video metadata and available formats.
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary with metadata and formats
            
        Raises:
            InvalidUrlError: If URL is invalid
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Fetching video info for URL: {url}")
            
            # Extract metadata
            metadata = self.video_processor.extract_metadata(url)
            
            # Get available formats
            formats = self.video_processor.get_available_formats(url)
            
            # Convert to frontend format
            formats_list = self.video_processor.formats_to_frontend_list(formats)
            
            logger.info(f"Successfully fetched {len(formats_list)} formats for video: {metadata.title}")
            
            return {
                "meta": {
                    "id": metadata.id,
                    "title": metadata.title,
                    "uploader": metadata.uploader,
                    "duration": metadata.duration,
                    "thumbnail": metadata.thumbnail
                },
                "formats": formats_list
            }
        except InvalidUrlError as e:
            logger.warning(f"Invalid URL provided: {url}")
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
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary with metadata
            
        Raises:
            InvalidUrlError: If URL is invalid
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Fetching metadata for URL: {url}")
            
            metadata = self.video_processor.extract_metadata(url)
            
            return {
                "id": metadata.id,
                "title": metadata.title,
                "uploader": metadata.uploader,
                "duration": metadata.duration,
                "thumbnail": metadata.thumbnail
            }
        except Exception as e:
            logger.error(f"Error fetching metadata for URL {url}: {str(e)}")
            raise
    
    def get_formats_only(self, url: str) -> List[Dict[str, Any]]:
        """
        Get only available formats without metadata.
        
        Args:
            url: YouTube URL
            
        Returns:
            List of format dictionaries
            
        Raises:
            InvalidUrlError: If URL is invalid
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Fetching formats for URL: {url}")
            
            formats = self.video_processor.get_available_formats(url)
            formats_list = self.video_processor.formats_to_frontend_list(formats)
            
            logger.info(f"Successfully fetched {len(formats_list)} formats")
            
            return formats_list
        except Exception as e:
            logger.error(f"Error fetching formats for URL {url}: {str(e)}")
            raise
