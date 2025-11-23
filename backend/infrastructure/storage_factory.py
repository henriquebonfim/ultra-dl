"""
Storage Factory

Factory for creating appropriate storage repository implementation based on environment.
This factory follows the Factory pattern to encapsulate the logic for selecting between
different storage backends (local filesystem vs Google Cloud Storage) based on runtime
configuration.

The factory enables dependency inversion by allowing the application layer to request
a storage repository without knowing which concrete implementation will be provided.
"""

import os
from typing import Optional

from domain.file_storage.storage_repository import IFileStorageRepository
from infrastructure.local_file_storage_repository import LocalFileStorageRepository


class StorageFactory:
    """
    Factory for creating storage repository implementations.
    
    This factory selects the appropriate storage backend based on environment
    configuration, allowing the application to remain agnostic to the specific
    storage implementation being used.
    
    Selection Logic:
    - If GCS_BUCKET_NAME is configured, attempt to use GCS storage
    - Otherwise, fall back to local filesystem storage
    
    The factory ensures that the application layer depends only on the
    IFileStorageRepository interface, not on concrete implementations.
    """
    
    @staticmethod
    def create_storage() -> IFileStorageRepository:
        """
        Create storage repository based on environment configuration.
        
        Selects between LocalFileStorageRepository and GCSStorageRepository
        based on the presence of GCS_BUCKET_NAME environment variable.
        
        Returns:
            IFileStorageRepository implementation (either local or GCS)
            
        Raises:
            ValueError: If GCS is configured but required parameters are missing
            RuntimeError: If storage initialization fails
            
        Environment Variables:
            GCS_BUCKET_NAME: If set, enables GCS storage
            DOWNLOAD_DIR: Base directory for local storage (default: /tmp/ultra-dl)
            GOOGLE_APPLICATION_CREDENTIALS: Path to GCS service account key (optional)
            
        Examples:
            >>> # Local storage (no GCS configured)
            >>> os.environ['DOWNLOAD_DIR'] = '/data/downloads'
            >>> storage = StorageFactory.create_storage()
            >>> isinstance(storage, LocalFileStorageRepository)
            True
            
            >>> # GCS storage (GCS configured)
            >>> os.environ['GCS_BUCKET_NAME'] = 'my-bucket'
            >>> storage = StorageFactory.create_storage()
            >>> isinstance(storage, GCSStorageRepository)
            True
        """
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if gcs_bucket_name:
            # GCS is configured, attempt to use GCS storage
            return StorageFactory._create_gcs_storage(gcs_bucket_name)
        else:
            # No GCS configured, use local filesystem storage
            return StorageFactory._create_local_storage()
    
    @staticmethod
    def _create_local_storage() -> IFileStorageRepository:
        """
        Create local filesystem storage repository.
        
        Returns:
            LocalFileStorageRepository instance
            
        Raises:
            RuntimeError: If local storage initialization fails
        """
        try:
            download_dir = os.getenv("DOWNLOAD_DIR", "/tmp/ultra-dl")
            storage = LocalFileStorageRepository(download_dir)
            
            print(f"Storage factory: Using local filesystem storage at {download_dir}")
            return storage
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize local storage: {e}") from e
    
    @staticmethod
    def _create_gcs_storage(bucket_name: str) -> IFileStorageRepository:
        """
        Create Google Cloud Storage repository.
        
        Args:
            bucket_name: Name of the GCS bucket to use
            
        Returns:
            GCSStorageRepository instance
            
        Raises:
            ValueError: If bucket_name is empty
            RuntimeError: If GCS storage initialization fails
        """
        if not bucket_name or not bucket_name.strip():
            raise ValueError("GCS_BUCKET_NAME cannot be empty")
        
        try:
            from infrastructure.gcs_storage_repository import GCSStorageRepository
            
            storage = GCSStorageRepository(bucket_name)
            print(f"Storage factory: Using GCS storage with bucket {bucket_name}")
            return storage
            
        except Exception as e:
            # If GCS initialization fails, fall back to local storage
            print(f"Warning: Failed to initialize GCS storage: {e}")
            print("Falling back to local filesystem storage")
            return StorageFactory._create_local_storage()
