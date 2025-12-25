"""
Storage Factory

Factory for creating the storage repository implementation.

This simplified factory always returns a local filesystem storage adapter to
avoid external cloud dependencies. The application layer remains decoupled from
the concrete implementation via the `IFileStorageRepository` interface.
"""

from src.domain.file_storage.storage_repository import IFileStorageRepository
from src.infrastructure.local_file_storage_repository import LocalFileStorageRepository


class StorageFactory:
    """Factory that returns a local filesystem storage repository."""

    @staticmethod
    def create_storage() -> IFileStorageRepository:
        """
        Create local filesystem storage repository.

        Returns:
            Local `IFileStorageRepository` implementation.

        Environment Variables:
            DOWNLOAD_DIR: Base directory for local storage (default: /tmp/downloaded_files)
        """
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
            from os import getenv

            download_dir = getenv("DOWNLOAD_DIR", "/tmp/downloaded_files")
            storage = LocalFileStorageRepository(download_dir)
            print(f"Storage factory: Using local filesystem storage at {download_dir}")
            return storage
        except Exception as e:
            raise RuntimeError(f"Failed to initialize local storage: {e}") from e
