"""
Error Handling Module

Defines domain exceptions and error categories for the application.
Domain exceptions are pure and have no external dependencies.
Application exceptions can have infrastructure concerns like logging.
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCategory(Enum):
    """Error category enumeration for structured error handling."""

    INVALID_URL = "invalid_url"
    VIDEO_UNAVAILABLE = "video_unavailable"
    FORMAT_NOT_SUPPORTED = "format_not_supported"
    DOWNLOAD_FAILED = "download_failed"
    FILE_TOO_LARGE = "file_too_large"
    RATE_LIMITED = "rate_limited"
    SYSTEM_ERROR = "system_error"
    JOB_NOT_FOUND = "job_not_found"
    INVALID_REQUEST = "invalid_request"
    NETWORK_ERROR = "network_error"
    FILE_NOT_FOUND = "file_not_found"
    FILE_EXPIRED = "file_expired"
    GEO_BLOCKED = "geo_blocked"
    LOGIN_REQUIRED = "login_required"
    PLATFORM_RATE_LIMITED = "platform_rate_limited"
    DOWNLOAD_TIMEOUT = "download_timeout"


# User-friendly error messages with actionable guidance
ERROR_MESSAGES: Dict[ErrorCategory, Dict[str, str]] = {
    ErrorCategory.INVALID_URL: {
        "title": "Invalid YouTube URL",
        "message": "Please check the URL and make sure it's a valid YouTube link.",
        "action": "Try copying the URL directly from YouTube.",
    },
    ErrorCategory.VIDEO_UNAVAILABLE: {
        "title": "Video Not Available",
        "message": "This video cannot be downloaded. It may be private, deleted, or restricted.",
        "action": "Try a different video or check if the video is publicly available.",
    },
    ErrorCategory.FORMAT_NOT_SUPPORTED: {
        "title": "Format Not Supported",
        "message": "The selected video format is not available for download.",
        "action": "Please choose a different quality or format option.",
    },
    ErrorCategory.DOWNLOAD_FAILED: {
        "title": "Download Failed",
        "message": "The download could not be completed due to an error.",
        "action": "Please try again. If the problem persists, try a different format.",
    },
    ErrorCategory.FILE_TOO_LARGE: {
        "title": "File Too Large",
        "message": "The selected video file exceeds the maximum allowed size.",
        "action": "Try selecting a lower quality format to reduce file size.",
    },
    ErrorCategory.RATE_LIMITED: {
        "title": "Too Many Requests",
        "message": "You've made too many requests in a short time.",
        "action": "Please wait a moment before trying again.",
    },
    ErrorCategory.SYSTEM_ERROR: {
        "title": "System Error",
        "message": "An unexpected error occurred while processing your request.",
        "action": "Please try again later. If the problem persists, contact support.",
    },
    ErrorCategory.JOB_NOT_FOUND: {
        "title": "Job Not Found",
        "message": "The requested download job could not be found or has expired.",
        "action": "Please start a new download.",
    },
    ErrorCategory.INVALID_REQUEST: {
        "title": "Invalid Request",
        "message": "The request is missing required information or contains invalid data.",
        "action": "Please check your input and try again.",
    },
    ErrorCategory.NETWORK_ERROR: {
        "title": "Network Error",
        "message": "Unable to connect to YouTube or download the video.",
        "action": "Check your internet connection and try again.",
    },
    ErrorCategory.FILE_NOT_FOUND: {
        "title": "File Not Found",
        "message": "The requested file could not be found or has been deleted.",
        "action": "Please download the video again.",
    },
    ErrorCategory.FILE_EXPIRED: {
        "title": "File Expired",
        "message": "The download link has expired. Files are available for 10 minutes after download.",
        "action": "Please download the video again to get a new link.",
    },
    ErrorCategory.GEO_BLOCKED: {
        "title": "Content Not Available in Your Region",
        "message": "This video is not available for download in your current location due to geographic restrictions.",
        "action": "Try using a VPN or check if the video is available in your region on YouTube directly.",
    },
    ErrorCategory.LOGIN_REQUIRED: {
        "title": "Login Required",
        "message": "This video requires you to be logged in to YouTube to access it.",
        "action": "This type of content cannot be downloaded automatically. Please watch it directly on YouTube.",
    },
    ErrorCategory.PLATFORM_RATE_LIMITED: {
        "title": "Platform Rate Limited",
        "message": "YouTube is temporarily limiting download requests. This is normal and helps prevent abuse.",
        "action": "Please wait a few minutes before trying again. Avoid making too many requests in a short time.",
    },
    ErrorCategory.DOWNLOAD_TIMEOUT: {
        "title": "Download Timeout",
        "message": "The download took too long to complete. This usually happens with large files or slow internet connections.",
        "action": "Try selecting a lower quality format, or check your internet connection and try again.",
    },
}


# ============================================================================
# Domain Exceptions (Pure - No External Dependencies)
# ============================================================================

class DomainError(Exception):
    """
    Base exception for all domain errors.
    
    Domain exceptions are pure and have no external dependencies.
    They can optionally wrap original errors for context.
    """
    
    def __init__(self, message: str, original_error: Exception = None):
        """
        Initialize domain error.
        
        Args:
            message: Error message
            original_error: Optional original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error


class MetadataExtractionError(DomainError):
    """
    Raised when video metadata extraction fails.
    
    This is a generic domain exception that doesn't depend on
    any specific extraction library (e.g., yt-dlp).
    """
    pass


class FormatNotFoundError(DomainError):
    """
    Raised when a requested video format is not available.
    
    This occurs when a user requests a specific format that
    doesn't exist for the given video.
    """
    pass


class VideoProcessingError(DomainError):
    """
    Base exception for video processing errors.
    
    Generic error for any video processing operation that fails.
    """
    pass


class InvalidUrlError(DomainError):
    """
    Raised when URL validation fails.
    
    This is typically raised by the YouTubeUrl value object.
    """
    pass


# ============================================================================
# Application Layer Exceptions (Can have infrastructure concerns)
# ============================================================================

class ApplicationError(Exception):
    """
    Base application error with category and user-friendly messaging.
    
    This is an application-layer concern that bridges domain errors
    with user-facing error messages and HTTP responses.
    
    Note: Logging is handled by application layer event handlers,
    not directly in this exception class.
    """

    def __init__(
        self,
        category: ErrorCategory,
        technical_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize application error.

        Args:
            category: Error category
            technical_message: Technical error details for logging
            context: Additional context information
        """
        self.category = category
        self.technical_message = technical_message or ""
        self.context = context or {}

        # Get user-friendly message
        error_info = ERROR_MESSAGES.get(
            category, ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]
        )
        self.title = error_info["title"]
        self.message = error_info["message"]
        self.action = error_info["action"]

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for API response.

        Returns:
            Dictionary with error information
        """
        return {
            "error": self.category.value,
            "title": self.title,
            "message": self.message,
            "action": self.action,
        }


# ============================================================================
# Note: Error categorization has been moved to application layer
# ============================================================================
# The categorize_ytdlp_error function has been moved to application/video_service.py
# as _categorize_extraction_error() to maintain proper DDD layer separation.
# Domain layer should not depend on external libraries like yt-dlp.
# ============================================================================


class RateLimitExceededError(ApplicationError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        category: ErrorCategory,
        technical_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(category, technical_message, context)
        self.http_status_code = 429


def create_error_response(
    category: ErrorCategory,
    technical_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
) -> tuple[Dict[str, Any], int]:
    """
    Create a structured error response for API endpoints.
    
    Note: Logging should be handled by application layer event handlers,
    not directly in this function.

    Args:
        category: Error category
        technical_message: Technical error details for logging
        context: Additional context information
        status_code: HTTP status code

    Returns:
        Tuple of (error_dict, status_code)
    """
    error = ApplicationError(category, technical_message, context)
    return error.to_dict(), status_code



