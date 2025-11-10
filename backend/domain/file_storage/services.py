"""
File Storage Services

Domain services for temporary file management.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List

from .entities import DownloadedFile
from .repositories import FileRepository


class FileNotFoundError(Exception):
    """Raised when a file is not found."""
    pass


class FileExpiredError(Exception):
    """Raised when a file has expired."""
    pass


class FileManager:
    """
    Domain service for managing temporary file storage.
    
    Coordinates file registration, token-based access, and cleanup.
    """
    
    def __init__(self, file_repository: FileRepository):
        """
        Initialize FileManager with repository.
        
        Args:
            file_repository: Repository for file metadata persistence
        """
        self.file_repo = file_repository
    
    def register_file(self, file_path: str, job_id: str, filename: str, 
                     ttl_minutes: int = 10) -> DownloadedFile:
        """
        Register a downloaded file with token-based access.
        
        Args:
            file_path: Path to the downloaded file
            job_id: Associated job ID
            filename: Original filename
            ttl_minutes: Time to live in minutes
            
        Returns:
            DownloadedFile entity with generated token
            
        Raises:
            Exception: If file registration fails
        """
        # Verify file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create file entity
        file = DownloadedFile.create(file_path, job_id, filename, ttl_minutes)
        
        # Save to repository
        if not self.file_repo.save(file):
            raise Exception("Failed to save file metadata to repository")
        
        return file
    
    def get_file_by_token(self, token: str) -> DownloadedFile:
        """
        Retrieve file by access token.
        
        Args:
            token: File access token
            
        Returns:
            DownloadedFile entity
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileExpiredError: If file has expired
        """
        file = self.file_repo.get_by_token(token)
        
        if file is None:
            raise FileNotFoundError(f"File not found for token: {token}")
        
        if file.is_expired():
            # Clean up expired file
            self.delete_file(token)
            raise FileExpiredError(f"File has expired: {token}")
        
        return file
    
    def get_file_by_job_id(self, job_id: str) -> Optional[DownloadedFile]:
        """
        Retrieve file by job ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            DownloadedFile if found, None otherwise
        """
        file = self.file_repo.get_by_job_id(job_id)
        
        if file and file.is_expired():
            self.delete_file(file.token)
            return None
        
        return file
    
    def delete_file(self, token: str, delete_physical: bool = True) -> bool:
        """
        Delete file metadata and optionally the physical file.
        
        Args:
            token: File access token
            delete_physical: Whether to delete the physical file
            
        Returns:
            True if successful
        """
        # Get file metadata
        file = self.file_repo.get_by_token(token)
        
        # Delete metadata from repository
        metadata_deleted = self.file_repo.delete(token)
        
        # Delete physical file if requested
        if delete_physical and file:
            self._delete_physical_file(file.file_path)
        
        return metadata_deleted
    
    def cleanup_expired_files(self) -> int:
        """
        Clean up expired files.
        
        Removes both metadata and physical files.
        
        Returns:
            Number of files cleaned up
        """
        expired_files = self.file_repo.get_expired_files()
        
        count = 0
        for file in expired_files:
            try:
                # Delete metadata
                self.file_repo.delete(file.token)
                
                # Delete physical file
                self._delete_physical_file(file.file_path)
                
                count += 1
            except Exception as e:
                print(f"Error cleaning up file {file.token}: {e}")
        
        return count
    
    def _delete_physical_file(self, file_path: str) -> bool:
        """
        Delete physical file or directory.
        
        Args:
            file_path: Path to file or directory
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            path = Path(file_path)
            
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                os.remove(path)
            
            return True
        except Exception as e:
            print(f"Error deleting physical file {file_path}: {e}")
            return False
    
    def get_download_url(self, token: str, base_url: str = "/downloads") -> str:
        """
        Get download URL for a file.
        
        Args:
            token: File access token
            base_url: Base URL for downloads
            
        Returns:
            Download URL
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileExpiredError: If file has expired
        """
        file = self.get_file_by_token(token)
        return file.generate_download_url(base_url)
    
    def validate_token(self, token: str) -> bool:
        """
        Validate if a token is valid and not expired.
        
        Args:
            token: File access token
            
        Returns:
            True if valid, False otherwise
        """
        try:
            file = self.file_repo.get_by_token(token)
            return file is not None and not file.is_expired()
        except Exception:
            return False
    
    def get_file_info(self, token: str) -> dict:
        """
        Get file information for API response.
        
        Args:
            token: File access token
            
        Returns:
            Dictionary with file information
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileExpiredError: If file has expired
        """
        file = self.get_file_by_token(token)
        
        return {
            "token": file.token,
            "filename": file.filename,
            "filesize": file.filesize,
            "filesize_mb": file.get_filesize_mb(),
            "expires_at": file.expires_at.isoformat(),
            "remaining_seconds": file.get_remaining_seconds(),
            "download_url": file.generate_download_url()
        }
