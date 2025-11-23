"""
Google Cloud Storage Repository Implementation

Concrete implementation of IFileStorageRepository for Google Cloud Storage operations.
This implementation uses the google-cloud-storage library to perform file operations
on GCS, following the repository pattern to keep infrastructure concerns separate
from domain logic.
"""

from typing import Optional, BinaryIO
from io import BytesIO
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound

from domain.file_storage.storage_repository import IFileStorageRepository


class GCSStorageRepository(IFileStorageRepository):
    """
    Google Cloud Storage implementation of IFileStorageRepository.
    
    This implementation handles file operations on Google Cloud Storage,
    providing a concrete implementation of the abstract IFileStorageRepository
    interface. It uses the google-cloud-storage library for all GCS operations.
    
    Thread Safety:
        This implementation is thread-safe. The GCS client handles concurrent
        operations safely.
    
    Attributes:
        bucket_name: Name of the GCS bucket for file storage
        client: Google Cloud Storage client instance
        bucket: GCS bucket object
    """
    
    def __init__(self, bucket_name: str):
        """
        Initialize the GCS storage repository.
        
        Args:
            bucket_name: Name of the GCS bucket to use for storage
            
        Raises:
            ValueError: If bucket_name is empty
            GoogleCloudError: If GCS client initialization fails
        """
        if not bucket_name or not bucket_name.strip():
            raise ValueError("bucket_name cannot be empty")
        
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def generate_signed_url(self, blob_name: str, ttl_minutes: int = 10) -> str:
        """
        Generate a signed URL for temporary access to a blob.
        
        This method is specific to GCS and not part of the IFileStorageRepository
        interface. It provides time-limited access to files without authentication.
        
        Args:
            blob_name: Name of the blob (file path) in the bucket
            ttl_minutes: Time-to-live in minutes for the signed URL (default: 10)
            
        Returns:
            Signed URL string that provides temporary access to the blob
            
        Raises:
            NotFound: If the blob doesn't exist
            GoogleCloudError: If signed URL generation fails
        """
        from datetime import timedelta
        
        try:
            blob = self.bucket.blob(blob_name)
            
            # Check if blob exists
            if not blob.exists():
                raise NotFound(f"Blob not found: {blob_name}")
            
            # Generate signed URL with expiration
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=ttl_minutes),
                method="GET"
            )
            
            return signed_url
            
        except NotFound:
            raise
        except Exception as e:
            raise GoogleCloudError(f"Failed to generate signed URL: {e}") from e
    
    def save(self, file_path: str, content: BinaryIO) -> bool:
        """
        Save file content to GCS.
        
        Implements IFileStorageRepository.save() for Google Cloud Storage.
        Stores the binary content at the specified path (blob name) in the bucket.
        
        Args:
            file_path: Relative path for the file (e.g., 'videos/abc123/video.mp4')
            content: Binary file content as a file-like object (BinaryIO)
            
        Returns:
            True if the file was successfully saved, False otherwise
            
        Raises:
            PermissionError: If there are insufficient permissions to write
            IOError: If there are I/O errors during the operation
            ValueError: If file_path is empty or invalid
        """
        try:
            # Validate file_path
            if not file_path or not file_path.strip():
                raise ValueError("file_path cannot be empty")
            
            # Create blob reference
            blob = self.bucket.blob(file_path)
            
            # Upload content from file-like object
            # Reset position to beginning if possible
            if hasattr(content, 'seek'):
                content.seek(0)
            
            blob.upload_from_file(content)
            
            return True
            
        except ValueError:
            raise
        except GoogleCloudError as e:
            if "403" in str(e) or "permission" in str(e).lower():
                raise PermissionError(f"Insufficient permissions to write to GCS: {e}") from e
            raise IOError(f"Failed to save file to GCS: {e}") from e
        except Exception as e:
            raise IOError(f"Failed to save file: {e}") from e
    
    def get(self, file_path: str) -> Optional[BinaryIO]:
        """
        Retrieve file content from GCS.
        
        Implements IFileStorageRepository.get() for Google Cloud Storage.
        Returns a binary stream of the file content.
        
        Args:
            file_path: Relative path to the file (e.g., 'downloads/video.mp4')
            
        Returns:
            Binary file content as BinaryIO if found, None if file doesn't exist
        """
        try:
            # Validate file_path
            if not file_path or not file_path.strip():
                return None
            
            # Create blob reference
            blob = self.bucket.blob(file_path)
            
            # Check if blob exists
            if not blob.exists():
                return None
            
            # Download content into BytesIO
            content = BytesIO()
            blob.download_to_file(content)
            
            # Reset position to beginning
            content.seek(0)
            return content
            
        except NotFound:
            # Blob doesn't exist
            return None
        except Exception:
            # Return None for any errors (as per interface contract)
            return None
    
    def delete(self, file_path: str) -> bool:
        """
        Delete a file from GCS.
        
        Implements IFileStorageRepository.delete() for Google Cloud Storage.
        This operation is idempotent - deleting a non-existent file returns True.
        
        Args:
            file_path: Relative path to the file (e.g., 'downloads/video.mp4')
            
        Returns:
            True if the file was deleted or didn't exist, False on failure
            
        Raises:
            PermissionError: If there are insufficient permissions to delete
            IOError: If there are I/O errors during the operation
        """
        try:
            # Validate file_path
            if not file_path or not file_path.strip():
                return True  # Idempotent - invalid path treated as success
            
            # Create blob reference
            blob = self.bucket.blob(file_path)
            
            # Check if blob exists
            if not blob.exists():
                return True  # Idempotent - non-existent file treated as success
            
            # Delete the blob
            blob.delete()
            
            return True
            
        except GoogleCloudError as e:
            if "403" in str(e) or "permission" in str(e).lower():
                raise PermissionError(f"Insufficient permissions to delete from GCS: {e}") from e
            raise IOError(f"Failed to delete file from GCS: {e}") from e
        except Exception as e:
            raise IOError(f"Failed to delete file: {e}") from e
    
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in GCS.
        
        Implements IFileStorageRepository.exists() for Google Cloud Storage.
        This method never raises exceptions - invalid paths return False.
        
        Args:
            file_path: Relative path to check (e.g., 'downloads/video.mp4')
            
        Returns:
            True if the file exists, False otherwise
        """
        try:
            # Handle empty or invalid paths
            if not file_path or not file_path.strip():
                return False
            
            # Create blob reference
            blob = self.bucket.blob(file_path)
            
            # Check if blob exists
            return blob.exists()
            
        except Exception:
            # Never raise exceptions - return False for errors
            return False
    
    def get_size(self, file_path: str) -> Optional[int]:
        """
        Get the size of a file in bytes from GCS.
        
        Implements IFileStorageRepository.get_size() for Google Cloud Storage.
        Returns the file size without downloading the entire file content.
        
        Args:
            file_path: Relative path to the file (e.g., 'downloads/video.mp4')
            
        Returns:
            File size in bytes if the file exists, None if file doesn't exist
            or if there's an error retrieving the size
        """
        try:
            # Handle empty or invalid paths
            if not file_path or not file_path.strip():
                return None
            
            # Create blob reference
            blob = self.bucket.blob(file_path)
            
            # Check if blob exists
            if not blob.exists():
                return None
            
            # Reload blob metadata to get size
            blob.reload()
            
            # Return blob size
            return blob.size
            
        except NotFound:
            # Blob doesn't exist
            return None
        except Exception:
            # Handle errors accessing blob metadata
            return None
