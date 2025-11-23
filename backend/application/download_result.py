"""
Download Result Value Object

Encapsulates the outcome of a download operation.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from domain.errors import ErrorCategory
from domain.job_management.entities import DownloadJob


@dataclass
class DownloadResult:
    """
    Value object representing the result of a download operation.
    
    Encapsulates success/failure state, job information, and error details.
    """
    
    success: bool
    job: DownloadJob
    download_url: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    error_message: Optional[str] = None
    
    @classmethod
    def create_success(cls, job: DownloadJob, download_url: str) -> 'DownloadResult':
        """
        Create a successful download result.
        
        Args:
            job: Completed download job
            download_url: URL to download the file
            
        Returns:
            DownloadResult indicating success
        """
        return cls(
            success=True,
            job=job,
            download_url=download_url
        )
    
    @classmethod
    def create_failure(
        cls,
        job: DownloadJob,
        error_category: ErrorCategory,
        error_message: str
    ) -> 'DownloadResult':
        """
        Create a failed download result.
        
        Args:
            job: Failed download job
            error_category: Category of error that occurred
            error_message: Human-readable error message
            
        Returns:
            DownloadResult indicating failure
        """
        return cls(
            success=False,
            job=job,
            error_category=error_category,
            error_message=error_message
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for serialization.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            'status': 'completed' if self.success else 'failed',
            'job_id': self.job.job_id,
            'download_url': self.download_url,
            'error': self.error_message,
            'error_category': self.error_category.value if self.error_category else None
        }
