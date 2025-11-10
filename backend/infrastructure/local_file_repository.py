"""
Local File Storage Repository

Infrastructure layer for local filesystem file operations.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class LocalFileStorageError(Exception):
    """Raised when local file storage operation fails."""
    pass


class LocalFileRepository:
    """
    Repository for local filesystem storage operations.
    
    Handles file storage, retrieval, and cleanup in /tmp/ultra-dl/.
    """
    
    def __init__(self, storage_dir: str = "/tmp/ultra-dl"):
        """
        Initialize local file repository.
        
        Args:
            storage_dir: Base directory for file storage
        """
        self.storage_dir = Path(storage_dir)
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Ensure storage directory exists."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise LocalFileStorageError(f"Failed to create storage directory: {e}")
    
    def is_available(self) -> bool:
        """
        Check if local storage is available.
        
        Returns:
            True if storage directory is accessible
        """
        return self.storage_dir.exists() and os.access(self.storage_dir, os.W_OK)
    
    def save_file(self, source_path: str, job_id: str, filename: str) -> str:
        """
        Save a file to local storage.
        
        Args:
            source_path: Path to source file
            job_id: Job identifier for organizing files
            filename: Original filename
            
        Returns:
            Path to saved file
            
        Raises:
            LocalFileStorageError: If save operation fails
        """
        try:
            # Create job-specific directory
            job_dir = self.storage_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            
            # Sanitize filename
            safe_filename = self._sanitize_filename(filename)
            
            # Destination path
            dest_path = job_dir / safe_filename
            
            # Copy file to storage
            shutil.copy2(source_path, dest_path)
            
            return str(dest_path)
            
        except Exception as e:
            raise LocalFileStorageError(f"Failed to save file: {e}")
    
    def get_file_path(self, job_id: str, filename: str) -> Optional[str]:
        """
        Get path to a stored file.
        
        Args:
            job_id: Job identifier
            filename: Filename
            
        Returns:
            Path to file if it exists, None otherwise
        """
        safe_filename = self._sanitize_filename(filename)
        file_path = self.storage_dir / job_id / safe_filename
        
        if file_path.exists():
            return str(file_path)
        return None
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file exists
        """
        try:
            return Path(file_path).exists()
        except Exception:
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                os.remove(path)
            
            # Clean up empty parent directory (job directory)
            parent = path.parent
            if parent.exists() and parent != self.storage_dir:
                try:
                    if not any(parent.iterdir()):  # Check if directory is empty
                        parent.rmdir()
                except Exception:
                    pass  # Ignore errors when cleaning up parent
            
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_file_size(self, file_path: str) -> Optional[int]:
        """
        Get size of a file in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes or None
        """
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace unsafe characters
        safe_chars = "".join(c for c in filename if c.isalnum() or c in " .-_()").strip()
        
        # Ensure filename is not empty
        if not safe_chars:
            safe_chars = "download"
        
        return safe_chars
    
    def cleanup_job_files(self, job_id: str) -> bool:
        """
        Clean up all files for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cleanup successful
        """
        try:
            job_dir = self.storage_dir / job_id
            
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
                return True
            
            return False
        except Exception as e:
            print(f"Error cleaning up job files for {job_id}: {e}")
            return False
