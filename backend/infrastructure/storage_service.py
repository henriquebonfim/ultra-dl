"""
Unified Storage Service

Provides automatic fallback from GCS to local storage.
"""

import os
from typing import Optional, Tuple
from pathlib import Path

from .gcs_repository import GCSRepository, GCSUploadError
from .local_file_repository import LocalFileRepository, LocalFileStorageError


class StorageService:
    """
    Unified storage service with automatic GCS to local fallback.
    
    Detects GCS configuration at startup and automatically falls back
    to local storage if GCS is unavailable.
    """
    
    def __init__(self, local_storage_dir: str = "/tmp/ultra-dl"):
        """
        Initialize storage service.
        
        Args:
            local_storage_dir: Directory for local file storage
        """
        self.local_repo = LocalFileRepository(local_storage_dir)
        self.gcs_repo = GCSRepository()
        
        # Detect storage mode at initialization
        self.use_gcs = self._detect_gcs_availability()
        
        if self.use_gcs:
            print("Storage: Using Google Cloud Storage (GCS)")
        else:
            print("Storage: Using local filesystem storage")
    
    def _detect_gcs_availability(self) -> bool:
        """
        Detect if GCS is available and configured.
        
        Returns:
            True if GCS should be used, False for local storage
        """
        # Check if GCS is explicitly disabled
        if os.getenv('DISABLE_GCS', '').lower() == 'true':
            print("GCS explicitly disabled via DISABLE_GCS environment variable")
            return False
        
        # Check if GCS is available
        if not self.gcs_repo.is_available():
            print("GCS not available, falling back to local storage")
            return False
        
        return True
    
    def is_using_gcs(self) -> bool:
        """
        Check if currently using GCS.
        
        Returns:
            True if using GCS, False if using local storage
        """
        return self.use_gcs
    
    def save_file(self, source_path: str, job_id: str, filename: str) -> Tuple[str, bool]:
        """
        Save a file to storage (GCS or local with fallback).
        
        Args:
            source_path: Path to source file
            job_id: Job identifier
            filename: Original filename
            
        Returns:
            Tuple of (storage_path, is_gcs) where:
                - storage_path: Path or blob name where file is stored
                - is_gcs: True if stored in GCS, False if local
            
        Raises:
            LocalFileStorageError: If both GCS and local storage fail
        """
        if self.use_gcs:
            try:
                # Try GCS first
                blob_name = self.gcs_repo.generate_blob_name(job_id, filename)
                
                # Determine content type
                content_type = self._get_content_type(filename)
                
                # Upload to GCS
                self.gcs_repo.upload_file(source_path, blob_name, content_type)
                
                return blob_name, True
                
            except GCSUploadError as e:
                print(f"GCS upload failed, falling back to local storage: {e}")
                # Fall through to local storage
        
        # Use local storage (either by default or as fallback)
        try:
            local_path = self.local_repo.save_file(source_path, job_id, filename)
            return local_path, False
        except LocalFileStorageError as e:
            raise LocalFileStorageError(f"Failed to save file to storage: {e}")
    
    def file_exists(self, storage_path: str, is_gcs: bool = None) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            storage_path: Path or blob name
            is_gcs: True for GCS, False for local, None to auto-detect
            
        Returns:
            True if file exists
        """
        if is_gcs is None:
            is_gcs = self.use_gcs
        
        if is_gcs:
            return self.gcs_repo.blob_exists(storage_path)
        else:
            return self.local_repo.file_exists(storage_path)
    
    def delete_file(self, storage_path: str, is_gcs: bool = None) -> bool:
        """
        Delete a file from storage.
        
        Args:
            storage_path: Path or blob name
            is_gcs: True for GCS, False for local, None to auto-detect
            
        Returns:
            True if deleted successfully
        """
        if is_gcs is None:
            is_gcs = self.use_gcs
        
        if is_gcs:
            return self.gcs_repo.delete_blob(storage_path)
        else:
            return self.local_repo.delete_file(storage_path)
    
    def get_file_size(self, storage_path: str, is_gcs: bool = None) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            storage_path: Path or blob name
            is_gcs: True for GCS, False for local, None to auto-detect
            
        Returns:
            File size in bytes or None
        """
        if is_gcs is None:
            is_gcs = self.use_gcs
        
        if is_gcs:
            metadata = self.gcs_repo.get_blob_metadata(storage_path)
            return metadata.get('size') if metadata else None
        else:
            return self.local_repo.get_file_size(storage_path)
    
    def cleanup_job_files(self, job_id: str) -> bool:
        """
        Clean up all files for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cleanup successful
        """
        # Always try to clean up local files
        local_cleaned = self.local_repo.cleanup_job_files(job_id)
        
        # If using GCS, also clean up GCS files
        if self.use_gcs:
            # GCS cleanup would need to list and delete blobs with job_id prefix
            # This is handled by lifecycle rules in production
            pass
        
        return local_cleaned
    
    def _get_content_type(self, filename: str) -> str:
        """
        Determine content type from filename.
        
        Args:
            filename: Filename with extension
            
        Returns:
            MIME type string
        """
        ext = Path(filename).suffix.lower()
        
        content_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.flv': 'video/x-flv',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.opus': 'audio/opus',
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    def get_storage_info(self) -> dict:
        """
        Get information about current storage configuration.
        
        Returns:
            Dictionary with storage information
        """
        return {
            'storage_type': 'gcs' if self.use_gcs else 'local',
            'gcs_available': self.gcs_repo.is_available(),
            'local_available': self.local_repo.is_available(),
            'storage_dir': str(self.local_repo.storage_dir) if not self.use_gcs else None,
            'gcs_bucket': os.getenv('GCS_BUCKET_NAME') if self.use_gcs else None
        }
