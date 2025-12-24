"""
Local File Storage Repository Implementation

Concrete implementation of IFileStorageRepository for local filesystem operations.
This implementation uses os, shutil, and pathlib to perform file operations
on the local filesystem, following the repository pattern to keep infrastructure
concerns separate from domain logic.
"""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

from src.domain.file_storage.storage_repository import IFileStorageRepository


class LocalFileStorageRepository(IFileStorageRepository):
    """
    Local filesystem implementation of IFileStorageRepository.

    This implementation handles file operations on the local filesystem,
    providing a concrete implementation of the abstract IFileStorageRepository
    interface. It uses Python's standard library (os, shutil, pathlib) for
    all filesystem operations.

    Thread Safety:
        This implementation is thread-safe for concurrent read operations.
        Write operations use atomic file operations where possible.

    Attributes:
        base_path: Base directory path for file storage operations
    """

    def __init__(self, base_path: str = "/tmp/ultra-dl"):
        """
        Initialize the local file storage repository.

        Args:
            base_path: Base directory for file storage (default: /tmp/ultra-dl)
        """
        self.base_path = Path(base_path)
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """
        Ensure the base storage directory exists.

        Creates the base directory if it doesn't exist, including any
        necessary parent directories.

        Raises:
            PermissionError: If insufficient permissions to create directory
            OSError: If directory creation fails for other reasons
        """
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Insufficient permissions to create storage directory: {self.base_path}"
            ) from e
        except OSError as e:
            raise OSError(
                f"Failed to create storage directory: {self.base_path}"
            ) from e

    # IFileStorageRepository interface methods

    def save(self, file_path: str, content: BinaryIO) -> bool:
        """
        Save file content to storage.

        Implements IFileStorageRepository.save() for local filesystem.
        Stores the binary content at the specified path relative to base_path.

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

            # Construct full path
            full_path = self.base_path / file_path

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            with open(full_path, "wb") as f:
                # Read and write in chunks for memory efficiency
                while True:
                    chunk = content.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    f.write(chunk)

            return True

        except ValueError:
            raise
        except PermissionError:
            raise
        except (IOError, OSError) as e:
            raise IOError(f"Failed to save file: {e}") from e

    def get(self, file_path: str) -> Optional[BinaryIO]:
        """
        Retrieve file content from storage.

        Implements IFileStorageRepository.get() for local filesystem.
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

            # Construct full path
            full_path = self.base_path / file_path

            # Check if file exists and is a file (not directory)
            if not full_path.exists() or not full_path.is_file():
                return None

            # Read file content into BytesIO for consistency
            with open(full_path, "rb") as f:
                content = BytesIO(f.read())

            # Reset position to beginning
            content.seek(0)
            return content

        except (OSError, ValueError):
            # Return None for any errors (as per interface contract)
            return None

    def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Implements IFileStorageRepository.delete() for local filesystem.
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

            # Construct full path
            full_path = self.base_path / file_path

            # If path doesn't exist, consider it a success (idempotent)
            if not full_path.exists():
                return True

            # Only delete files, not directories (as per interface contract)
            if full_path.is_file():
                full_path.unlink()

            return True

        except PermissionError:
            raise
        except (IOError, OSError) as e:
            raise IOError(f"Failed to delete file: {e}") from e

    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists at the specified path.

        Implements IFileStorageRepository.exists() for local filesystem.
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

            # Construct full path
            full_path = self.base_path / file_path

            # Check if exists and is a file (not directory)
            return full_path.exists() and full_path.is_file()

        except (OSError, ValueError):
            # Never raise exceptions - return False for errors
            return False

    def get_size(self, file_path: str) -> Optional[int]:
        """
        Get the size of a file in bytes.

        Implements IFileStorageRepository.get_size() for local filesystem.
        Returns the file size without reading the entire file content.

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

            # Construct full path
            full_path = self.base_path / file_path

            # Check if path exists
            if not full_path.exists():
                return None

            # Only return size for files, not directories
            if full_path.is_file():
                return full_path.stat().st_size

            # Return None for directories
            return None

        except (OSError, ValueError):
            # Handle errors accessing file stats
            return None
