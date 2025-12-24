"""
Video Processing Entities

Domain entities for video metadata and format information.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from .value_objects import FormatType


@dataclass
class VideoMetadata:
    """
    Entity representing YouTube video metadata.
    
    Contains essential information about a video extracted from yt-dlp.
    """
    id: str
    title: str
    uploader: str
    duration: int  # in seconds
    thumbnail: str
    url: str
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.id:
            raise ValueError("Video ID is required")
        if not self.title:
            raise ValueError("Video title is required")
        if self.duration < 0:
            raise ValueError("Duration must be non-negative")
    
    def get_duration_formatted(self) -> str:
        """Return duration in HH:MM:SS format."""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"


@dataclass
class VideoFormat:
    """
    Entity representing a video format option.
    
    Contains format details including resolution, codecs, and file size.
    """
    format_id: str
    extension: str
    resolution: str
    height: int
    width: Optional[int] = None
    filesize: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    quality_label: Optional[str] = None
    format_note: Optional[str] = None
    format_type: FormatType = FormatType.VIDEO_AUDIO
    
    def __post_init__(self):
        """Validate and determine format type."""
        if not self.format_id:
            raise ValueError("Format ID is required")
        if not self.extension:
            raise ValueError("Extension is required")
        
        # Determine format type based on codecs
        if self.video_codec and self.video_codec != "none" and self.audio_codec and self.audio_codec != "none":
            self.format_type = FormatType.VIDEO_AUDIO
        elif self.video_codec == "none" or (not self.video_codec and self.audio_codec):
            self.format_type = FormatType.AUDIO_ONLY
        else:
            self.format_type = FormatType.VIDEO_ONLY
    
    def get_filesize_mb(self) -> Optional[float]:
        """Return filesize in MB if available."""
        if self.filesize:
            return round(self.filesize / (1024 * 1024), 2)
        return None
    
    def get_filesize_formatted(self) -> str:
        """Return human-readable filesize."""
        if not self.filesize:
            return "Unknown"
        
        size_mb = self.filesize / (1024 * 1024)
        if size_mb < 1024:
            return f"{size_mb:.1f} MB"
        else:
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
    
    def is_video_only(self) -> bool:
        """Check if format is video-only."""
        return self.format_type == FormatType.VIDEO_ONLY
    
    def is_audio_only(self) -> bool:
        """Check if format is audio-only."""
        return self.format_type == FormatType.AUDIO_ONLY
    
    def has_both_codecs(self) -> bool:
        """Check if format has both video and audio."""
        return self.format_type == FormatType.VIDEO_AUDIO
    
    def calculate_quality_label(self) -> str:
        """
        Calculate quality label based on height.
        
        Returns: Ultra, Excellent, Great, Good, or Standard
        """
        if self.height >= 2160:
            return "Ultra"
        elif self.height >= 1440:
            return "Excellent"
        elif self.height >= 1080:
            return "Great"
        elif self.height >= 720:
            return "Good"
        else:
            return "Standard"
