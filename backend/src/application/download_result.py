"""
Download Result Value Object

Simplified value object representing the outcome of a download operation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DownloadResult:
    """
    Simplified value object representing the result of a download operation.
    
    Attributes:
        success: Whether the download succeeded
        file_path: Path to the downloaded file (if successful)
        error_message: Human-readable error message (if failed)
        error_type: Error category/type (if failed)
    """
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
