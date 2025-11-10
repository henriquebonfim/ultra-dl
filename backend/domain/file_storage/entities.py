"""
File Storage Entities

Domain entities for downloaded file management.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import secrets


@dataclass
class DownloadedFile:
    """
    Entity representing a downloaded file with expiration tracking.
    
    Manages file metadata and token-based access control.
    """
    file_path: str
    token: str
    job_id: str
    filename: str
    expires_at: datetime
    created_at: datetime
    filesize: Optional[int] = None
    
    @classmethod
    def create(cls, file_path: str, job_id: str, filename: str, 
               ttl_minutes: int = 10) -> 'DownloadedFile':
        """
        Factory method to create a new downloaded file entry.
        
        Args:
            file_path: Path to the downloaded file
            job_id: Associated job ID
            filename: Original filename
            ttl_minutes: Time to live in minutes (default: 10)
            
        Returns:
            New DownloadedFile instance
        """
        now = datetime.utcnow()
        token = cls._generate_token()
        expires_at = now + timedelta(minutes=ttl_minutes)
        
        # Get filesize if file exists
        filesize = None
        try:
            path = Path(file_path)
            if path.exists():
                filesize = path.stat().st_size
        except Exception:
            pass
        
        return cls(
            file_path=file_path,
            token=token,
            job_id=job_id,
            filename=filename,
            expires_at=expires_at,
            created_at=now,
            filesize=filesize
        )
    
    @staticmethod
    def _generate_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Token length in bytes (default: 32)
            
        Returns:
            URL-safe token string
        """
        return secrets.token_urlsafe(length)
    
    def is_expired(self) -> bool:
        """
        Check if file has expired.
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.utcnow() >= self.expires_at
    
    def get_remaining_time(self) -> timedelta:
        """
        Get remaining time until expiration.
        
        Returns:
            Timedelta representing remaining time (negative if expired)
        """
        return self.expires_at - datetime.utcnow()
    
    def get_remaining_seconds(self) -> int:
        """
        Get remaining seconds until expiration.
        
        Returns:
            Seconds remaining (0 if expired)
        """
        remaining = self.get_remaining_time()
        return max(0, int(remaining.total_seconds()))
    
    def generate_download_url(self, base_url: str = "/api/v1/downloads", api_base_url: Optional[str] = None) -> str:
        """
        Generate download URL with token.
        
        Args:
            base_url: Base URL for downloads
            api_base_url: The base URL of the API
            
        Returns:
            Full download URL
        """
        url = f"{base_url}/{self.token}"
        if api_base_url:
            return f"{api_base_url.rstrip('/')}{url}"
        return url
    
    def file_exists(self) -> bool:
        """
        Check if the physical file exists.
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            return Path(self.file_path).exists()
        except Exception:
            return False
    
    def get_filesize_mb(self) -> Optional[float]:
        """
        Get filesize in MB.
        
        Returns:
            Filesize in MB or None
        """
        if self.filesize:
            return round(self.filesize / (1024 * 1024), 2)
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "token": self.token,
            "job_id": self.job_id,
            "filename": self.filename,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "filesize": self.filesize
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DownloadedFile':
        """Create DownloadedFile from dictionary."""
        return cls(
            file_path=data["file_path"],
            token=data["token"],
            job_id=data["job_id"],
            filename=data["filename"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            filesize=data.get("filesize")
        )
