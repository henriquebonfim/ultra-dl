"""
Video Processing Value Objects

Immutable value objects for type safety and validation.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.errors import DomainError, InvalidUrlError


class FormatType(Enum):
    """Video format types based on codec availability."""

    VIDEO_AUDIO = "video+audio"
    VIDEO_ONLY = "video_only"
    AUDIO_ONLY = "audio_only"


@dataclass(frozen=True)
class YouTubeUrl:
    """
    Value object representing a validated YouTube URL.

    Ensures URL is valid before use in the system.
    """

    value: str

    def __post_init__(self):
        if not self._is_valid():
            raise InvalidUrlError(f"Invalid YouTube URL: {self.value}")

    def _is_valid(self) -> bool:
        """
        Validate YouTube URL format.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID
        """
        if not self.value or not isinstance(self.value, str):
            return False

        # Check for YouTube domain
        if "youtube.com" not in self.value and "youtu.be" not in self.value:
            return False

        # Basic URL pattern validation
        youtube_patterns = [
            r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
            r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+",
            r"(?:https?://)?(?:m\.)?youtube\.com/watch\?v=[\w-]+",
            r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        ]

        return any(re.match(pattern, self.value) for pattern in youtube_patterns)

    def extract_video_id(self) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r"(?:v=|/)([0-9A-Za-z_-]{11}).*",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.value)
            if match:
                return match.group(1)

        return None

    def __str__(self) -> str:
        return self.value


class InvalidFormatIdError(DomainError):
    """Raised when a format ID is invalid."""

    pass


@dataclass(frozen=True)
class FormatId:
    """
    Value object representing a validated yt-dlp format identifier.

    Supports:
    - Numeric formats: "137", "140"
    - Combined formats: "137+140", "bestvideo+bestaudio"
    - Keyword formats: "best", "worst", "bestaudio", "bestvideo"
    """

    value: str

    def __post_init__(self):
        if not self._is_valid():
            raise InvalidFormatIdError(f"Invalid format ID: {self.value}")

    def _is_valid(self) -> bool:
        """
        Validate format ID pattern.

        Valid patterns:
        - Numeric: 137, 140, 251
        - Combined: 137+140, bestvideo+bestaudio
        - Keywords: best, worst, bestaudio, bestvideo, worstaudio, worstvideo
        """
        if not self.value or not isinstance(self.value, str):
            return False

        # Keyword formats
        keywords = [
            "best",
            "worst",
            "bestaudio",
            "bestvideo",
            "worstaudio",
            "worstvideo",
            "auto",
        ]

        if self.value in keywords:
            return True

        # Numeric or combined formats
        # Pattern: one or more groups of digits or keywords separated by '+'
        pattern = r"^(\d+|best|worst|bestaudio|bestvideo|worstaudio|worstvideo)(\+(\d+|best|worst|bestaudio|bestvideo|worstaudio|worstvideo))*$"
        return bool(re.match(pattern, self.value))

    def is_combined(self) -> bool:
        """Check if this is a combined format (contains '+')."""
        return "+" in self.value

    def __str__(self) -> str:
        return self.value
