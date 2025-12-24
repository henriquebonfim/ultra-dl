"""
Value Object Factories

Factory functions for creating value objects with sensible defaults.
Supports both valid and invalid data generation for error testing.

Requirements: 7.1
"""

import secrets
from typing import Optional

from src.domain.job_management.value_objects import JobProgress
from src.domain.video_processing.value_objects import YouTubeUrl, FormatId
from src.domain.file_storage.value_objects import DownloadToken


def create_youtube_url(
    video_id: str = "dQw4w9WgXcQ",
    domain: str = "www.youtube.com",
    protocol: str = "https",
) -> YouTubeUrl:
    """
    Create a YouTubeUrl value object with sensible defaults.
    
    Args:
        video_id: YouTube video ID (11 characters)
        domain: YouTube domain (www.youtube.com, youtu.be, m.youtube.com)
        protocol: URL protocol (https, http)
        
    Returns:
        YouTubeUrl value object
        
    Raises:
        InvalidUrlError: If the constructed URL is invalid
    """
    if domain == "youtu.be":
        url = f"{protocol}://{domain}/{video_id}"
    else:
        url = f"{protocol}://{domain}/watch?v={video_id}"
    
    return YouTubeUrl(url)


def create_youtube_url_string(
    video_id: str = "dQw4w9WgXcQ",
    domain: str = "www.youtube.com",
    protocol: str = "https",
) -> str:
    """
    Create a YouTube URL string without validation.
    
    Useful for testing validation logic with both valid and invalid URLs.
    
    Args:
        video_id: YouTube video ID
        domain: YouTube domain
        protocol: URL protocol
        
    Returns:
        URL string (may be invalid)
    """
    if domain == "youtu.be":
        return f"{protocol}://{domain}/{video_id}"
    else:
        return f"{protocol}://{domain}/watch?v={video_id}"


def create_invalid_youtube_url_string(variant: str = "non_youtube") -> str:
    """
    Create an invalid YouTube URL string for error testing.
    
    Args:
        variant: Type of invalid URL to create
            - "non_youtube": URL from different domain
            - "malformed": Malformed URL structure
            - "missing_video_id": YouTube URL without video ID
            - "empty": Empty string
            - "none_like": String that looks like None
            
    Returns:
        Invalid URL string
    """
    variants = {
        "non_youtube": "https://vimeo.com/123456789",
        "malformed": "not-a-valid-url",
        "missing_video_id": "https://www.youtube.com/watch",
        "empty": "",
        "none_like": "None",
        "no_protocol": "youtube.com/watch?v=dQw4w9WgXcQ",
    }
    return variants.get(variant, variants["non_youtube"])


def create_format_id(
    format_id: str = "best",
) -> FormatId:
    """
    Create a FormatId value object.
    
    Args:
        format_id: Format identifier string
            - Keywords: "best", "worst", "bestaudio", "bestvideo"
            - Numeric: "137", "140", "251"
            - Combined: "137+140", "bestvideo+bestaudio"
            
    Returns:
        FormatId value object
        
    Raises:
        InvalidFormatIdError: If the format ID is invalid
    """
    return FormatId(format_id)


def create_invalid_format_id_string(variant: str = "empty") -> str:
    """
    Create an invalid format ID string for error testing.
    
    Args:
        variant: Type of invalid format ID to create
            - "empty": Empty string
            - "special_chars": Contains special characters
            - "invalid_keyword": Invalid keyword
            
    Returns:
        Invalid format ID string
    """
    variants = {
        "empty": "",
        "special_chars": "best@video",
        "invalid_keyword": "excellent",
        "spaces": "best video",
    }
    return variants.get(variant, variants["empty"])


def create_download_token(
    value: Optional[str] = None,
) -> DownloadToken:
    """
    Create a DownloadToken value object.
    
    Args:
        value: Token value (auto-generated if not provided)
            Must be at least 32 characters and URL-safe
            
    Returns:
        DownloadToken value object
        
    Raises:
        InvalidDownloadTokenError: If the token is invalid
    """
    if value is None:
        return DownloadToken.generate()
    return DownloadToken(value)


def create_valid_token_string(length: int = 43) -> str:
    """
    Create a valid token string without creating the value object.
    
    Args:
        length: Desired token length (minimum 32)
        
    Returns:
        Valid token string
    """
    return secrets.token_urlsafe(max(24, length))[:max(32, length)]


def create_invalid_token_string(variant: str = "too_short") -> str:
    """
    Create an invalid token string for error testing.
    
    Args:
        variant: Type of invalid token to create
            - "too_short": Less than 32 characters
            - "empty": Empty string
            - "special_chars": Contains invalid characters
            
    Returns:
        Invalid token string
    """
    variants = {
        "too_short": "abc123",
        "empty": "",
        "special_chars": "token!@#$%^&*(){}[]" + "a" * 20,
        "spaces": "token with spaces " + "a" * 20,
    }
    return variants.get(variant, variants["too_short"])


def create_job_progress(
    percentage: int = 0,
    phase: str = "initializing",
    speed: Optional[str] = None,
    eta: Optional[int] = None,
) -> JobProgress:
    """
    Create a JobProgress value object.
    
    Args:
        percentage: Progress percentage (0-100)
        phase: Current phase name
        speed: Download speed string (e.g., "1.5 MiB/s")
        eta: Estimated time remaining in seconds
        
    Returns:
        JobProgress value object
        
    Raises:
        ValueError: If percentage is out of range or phase is empty
    """
    return JobProgress(
        percentage=percentage,
        phase=phase,
        speed=speed,
        eta=eta,
    )


def create_progress_initial() -> JobProgress:
    """Create initial progress state."""
    return JobProgress.initial()


def create_progress_metadata_extraction() -> JobProgress:
    """Create metadata extraction progress state."""
    return JobProgress.metadata_extraction()


def create_progress_downloading(
    percentage: int = 50,
    speed: str = "1.5 MiB/s",
    eta: int = 60,
) -> JobProgress:
    """Create downloading progress state."""
    return JobProgress.downloading(percentage=percentage, speed=speed, eta=eta)


def create_progress_processing(percentage: int = 90) -> JobProgress:
    """Create processing progress state."""
    return JobProgress.processing(percentage=percentage)


def create_progress_completed() -> JobProgress:
    """Create completed progress state."""
    return JobProgress.completed()

