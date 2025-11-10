"""
Video Processing Services

Domain services for video metadata extraction and format processing.
"""

from typing import List, Dict, Any, Optional
from yt_dlp import YoutubeDL
from yt_dlp import utils as ytdlp_utils

from .entities import VideoMetadata, VideoFormat
from .value_objects import YouTubeUrl, InvalidUrlError, FormatType


class VideoProcessingError(Exception):
    """Base exception for video processing errors."""
    pass


class VideoProcessor:
    """
    Domain service for processing YouTube videos.
    
    Handles metadata extraction, format parsing, and validation using yt-dlp.
    """
    
    METADATA_OPTS = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best",
        "dump_single_json": True,
    }
    
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
            VideoProcessingError: If extraction fails
        """
        # Validate URL first
        youtube_url = YouTubeUrl(url)
        
        try:
            with YoutubeDL(self.METADATA_OPTS) as ydl:
                info = ydl.extract_info(str(youtube_url), download=False)
            
            return VideoMetadata(
                id=info.get("id", ""),
                title=info.get("title", "Unknown"),
                uploader=info.get("uploader", "Unknown"),
                duration=info.get("duration", 0),
                thumbnail=info.get("thumbnail", ""),
                url=str(youtube_url)
            )
        except ytdlp_utils.DownloadError as e:
            raise VideoProcessingError(f"Failed to extract metadata: {str(e)}")
        except Exception as e:
            raise VideoProcessingError(f"Unexpected error during metadata extraction: {str(e)}")
    
    def get_available_formats(self, url: str) -> List[VideoFormat]:
        """
        Get all available formats for a YouTube video.
        
        Args:
            url: YouTube URL
            
        Returns:
            List of VideoFormat entities sorted by height (descending)
            
        Raises:
            InvalidUrlError: If URL is invalid
            VideoProcessingError: If format extraction fails
        """
        # Validate URL first
        youtube_url = YouTubeUrl(url)
        
        try:
            with YoutubeDL(self.METADATA_OPTS) as ydl:
                info = ydl.extract_info(str(youtube_url), download=False)
            
            raw_formats = info.get("formats", [])
            formats = self._parse_formats(raw_formats)
            
            # Sort by height descending
            formats.sort(key=lambda f: f.height, reverse=True)
            
            return formats
        except ytdlp_utils.DownloadError as e:
            raise VideoProcessingError(f"Failed to extract formats: {str(e)}")
        except Exception as e:
            raise VideoProcessingError(f"Unexpected error during format extraction: {str(e)}")
    
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
                # Skip malformed formats
                print(f"Warning: Skipping malformed format: {e}")
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
    
    def _determine_resolution(self, fmt: Dict[str, Any], height: Optional[int], width: Optional[int]) -> str:
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
