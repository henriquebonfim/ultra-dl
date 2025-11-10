"""
Google Cloud Storage Repository

Infrastructure layer for GCS file operations.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import timedelta
from google.cloud import storage

from config.gcs_config import get_gcs_bucket, is_gcs_enabled


class GCSUploadError(Exception):
    """Raised when GCS upload fails."""
    pass


class GCSRepository:
    """
    Repository for Google Cloud Storage operations.
    
    Handles file uploads, signed URL generation, and cleanup.
    """
    
    def __init__(self):
        """Initialize GCS repository."""
        self.bucket = get_gcs_bucket()
    
    def is_available(self) -> bool:
        """
        Check if GCS is available.
        
        Returns:
            True if GCS is configured and available
        """
        return is_gcs_enabled() and self.bucket is not None
    
    def upload_file(self, local_path: str, blob_name: str, 
                   content_type: str = 'application/octet-stream') -> str:
        """
        Upload a file to GCS.
        
        Args:
            local_path: Path to local file
            blob_name: Name for the blob in GCS
            content_type: MIME type for the file
            
        Returns:
            GCS blob name
            
        Raises:
            GCSUploadError: If upload fails
        """
        if not self.is_available():
            raise GCSUploadError("GCS is not available")
        
        try:
            # Create blob reference
            blob = self.bucket.blob(blob_name)
            
            # Set content type
            blob.content_type = content_type
            
            # Upload file
            blob.upload_from_filename(local_path)
            
            print(f"Uploaded {local_path} to gs://{self.bucket.name}/{blob_name}")
            return blob_name
            
        except Exception as e:
            raise GCSUploadError(f"Failed to upload file to GCS: {e}")
    
    def generate_signed_url(self, blob_name: str, ttl_minutes: int = 10) -> str:
        """
        Generate a signed URL for downloading a blob.
        
        Args:
            blob_name: Name of the blob in GCS
            ttl_minutes: Time to live in minutes
            
        Returns:
            Signed URL string
            
        Raises:
            GCSUploadError: If signed URL generation fails
        """
        if not self.is_available():
            raise GCSUploadError("GCS is not available")
        
        try:
            blob = self.bucket.blob(blob_name)
            
            # Generate signed URL with expiration
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=ttl_minutes),
                method="GET"
            )
            
            return url
            
        except Exception as e:
            raise GCSUploadError(f"Failed to generate signed URL: {e}")
    
    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from GCS.
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deleted successfully
        """
        if not self.is_available():
            return False
        
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            print(f"Deleted blob: {blob_name}")
            return True
        except Exception as e:
            print(f"Error deleting blob {blob_name}: {e}")
            return False
    
    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if a blob exists in GCS.
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            True if blob exists
        """
        if not self.is_available():
            return False
        
        try:
            blob = self.bucket.blob(blob_name)
            return blob.exists()
        except Exception:
            return False
    
    def get_blob_metadata(self, blob_name: str) -> Optional[dict]:
        """
        Get metadata for a blob.
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Dictionary with blob metadata or None
        """
        if not self.is_available():
            return None
        
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()
            
            return {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated
            }
        except Exception as e:
            print(f"Error getting blob metadata: {e}")
            return None
    
    def generate_blob_name(self, job_id: str, filename: str) -> str:
        """
        Generate a unique blob name for GCS.
        
        Args:
            job_id: Job identifier
            filename: Original filename
            
        Returns:
            Blob name with job_id prefix
        """
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in " .-_()").strip()
        
        # Create blob name with job_id prefix for uniqueness
        return f"downloads/{job_id}/{safe_filename}"
