"""
Video Metadata Extractor Infrastructure Service

Infrastructure implementation of IVideoMetadataExtractor using yt-dlp.
This service handles all yt-dlp specific logic and error translation.
"""

from typing import List, Dict, Any, Optional
from yt_dlp import YoutubeDL
from yt_dlp import utils as ytdlp_utils

from domain.video_processing.repositories import IVideoMetadataExtractor
from domain.video_processing.entities import VideoMetadata, VideoFormat
from domain.video_processing.value_objects import YouTubeUrl, FormatType
from domain.errors import MetadataExtractionError


class VideoMetadataExtractor(IVideoMetadataExtractor):
    """
    yt-dlp based implementation of video metadata extraction.
    
    Handles all yt-dlp specific logic and error translation to domain exceptions.
    This keeps the domain layer pure and free from external dependencies.
    """
    
    METADATA_OPTS = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best",
        "dump_single_json": True,
    }
    
    def extract_metadata(self, url: YouTubeUrl) -> VideoMetadata:
        """
        Extract video metadata using yt-dlp.
        
        Args:
            url: Validated YouTubeUrl value object
            
        Returns:
            VideoMetadata entity
            
        Raises:
            MetadataExtractionError: If extraction fails
        """
        try:
            with YoutubeDL(self.METADATA_OPTS) as ydl:
                info = ydl.extract_info(str(url), download=False)
            
            return VideoMetadata(
                id=info.get("id", ""),
                title=info.get("title", "Unknown"),
                uploader=info.get("uploader", "Unknown"),
                duration=info.get("duration", 0),
                thumbnail=info.get("thumbnail", ""),
                url=str(url)
            )
        except ytdlp_utils.DownloadError as e:
            raise MetadataExtractionError(
                f"Failed to extract metadata: {str(e)}",
                original_error=e
            )
        except Exception as e:
            raise MetadataExtractionError(
                f"Unexpected error during metadata extraction: {str(e)}",
                original_error=e
            )
    
    def extract_formats(self, url: YouTubeUrl) -> List[VideoFormat]:
        """
        Extract available formats using yt-dlp.
        
        Args:
            url: Validated YouTubeUrl value object
            
        Returns:
            List of VideoFormat entities sorted by height (descending)
            
        Raises:
            MetadataExtractionError: If extraction fails
        """
        try:
            with YoutubeDL(self.METADATA_OPTS) as ydl:
                info = ydl.extract_info(str(url), download=False)
            
            raw_formats = info.get("formats", [])
            formats = self._parse_formats(raw_formats)
            
            # Sort by height descending
            formats.sort(key=lambda f: f.height, reverse=True)
            
            return formats
        except ytdlp_utils.DownloadError as e:
            raise MetadataExtractionError(
                f"Failed to extract formats: {str(e)}",
                original_error=e
            )
        except Exception as e:
            raise MetadataExtractionError(
                f"Unexpected error during format extraction: {str(e)}",
                original_error=e
            )
    
    def _parse_formats(self, raw_formats: List[Dict[str, Any]]) -> List[VideoFormat]:
        """
        Parse raw yt-dlp formats into VideoFormat entities.
        
        Fixes filesize extraction issue by checking multiple fields.
        
        Args:
            raw_formats: Raw format list from yt-dlp
            
        Returns:
            List of VideoFormat entities
        """
        formats = []
        
        for fmt in raw_formats:
            try:
                # Extract height and width
                height = fmt.get("height", 0)
                width = fmt.get("width")
                
                # Determine resolution string
                resolution = self._determine_resolution(fmt, height, width)
                
                # Fix filesize extraction - check multiple fields
                filesize = self._extract_filesize(fmt)
                
                # Extract codecs
                video_codec = fmt.get("vcodec", "none")
                audio_codec = fmt.get("acodec", "none")
                
                # Create VideoFormat entity
                video_format = VideoFormat(
                    format_id=str(fmt.get("format_id", "")),
                    extension=fmt.get("ext", "mp4"),
                    resolution=resolution,
                    height=height or 0,
                    width=width,
                    filesize=filesize,
                    video_codec=video_codec,
                    audio_codec=audio_codec,
                    quality_label=None,  # Will be calculated
                    format_note=fmt.get("format_note", "")
                )
                
                # Calculate quality label
                video_format.quality_label = video_format.calculate_quality_label()
                
                formats.append(video_format)
            except Exception as e:
                # Skip malformed formats - don't fail entire extraction
                # In production, this could be logged via event system
                continue
        
        return formats
    
    def _extract_filesize(self, fmt: Dict[str, Any]) -> Optional[int]:
        """
        Extract filesize from format dict.
        
        Fixes the filesize extraction issue by checking multiple fields:
        - filesize (exact size)
        - filesize_approx (approximate size)
        - Calculate from tbr and duration if available
        
        Args:
            fmt: Format dictionary from yt-dlp
            
        Returns:
            Filesize in bytes or None
        """
        # Try exact filesize first
        filesize = fmt.get("filesize")
        if filesize and filesize > 0:
            return filesize
        
        # Try approximate filesize
        filesize_approx = fmt.get("filesize_approx")
        if filesize_approx and filesize_approx > 0:
            return filesize_approx
        
        # Try to calculate from bitrate and duration
        tbr = fmt.get("tbr")  # Total bitrate in kbps
        duration = fmt.get("duration")
        
        if tbr and duration and tbr > 0 and duration > 0:
            # Calculate approximate size: (bitrate in kbps * duration in seconds * 1024) / 8
            estimated_size = int((tbr * duration * 1024) / 8)
            return estimated_size
        
        return None
    
    def _determine_resolution(
        self, 
        fmt: Dict[str, Any], 
        height: Optional[int], 
        width: Optional[int]
    ) -> str:
        """
        Determine resolution string for a format.
        
        Args:
            fmt: Format dictionary
            height: Video height
            width: Video width
            
        Returns:
            Resolution string (e.g., "1920x1080", "1080p", "audio only")
        """
        if height and width:
            return f"{width}x{height}"
        elif height:
            return f"{height}p"
        elif fmt.get("vcodec") == "none":
            return "audio only"
        else:
            return fmt.get("format_note", "unknown")
