"""
Video Processing Domain

Handles YouTube URL validation, metadata extraction, and format selection.
"""

from .entities import VideoFormat, VideoMetadata
from .services import VideoProcessingError, VideoProcessor
from .value_objects import FormatType, InvalidUrlError, YouTubeUrl

__all__ = [
    "VideoMetadata",
    "VideoFormat",
    "YouTubeUrl",
    "FormatType",
    "VideoProcessor",
    "InvalidUrlError",
    "VideoProcessingError",
]
