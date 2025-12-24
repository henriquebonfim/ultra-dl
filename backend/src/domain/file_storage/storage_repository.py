"""
File Storage Repository Interface

Abstract interface for physical file storage operations.
This abstraction allows the domain layer to remain infrastructure-agnostic
by defining contracts for file operations without depending on specific
storage implementations (local filesystem, cloud storage, etc.).

This interface follows the Repository pattern to maintain clean separation
between domain logic and infrastructure concerns, enabling dependency inversion
where infrastructure implementations depend on domain-defined contracts.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class IFileStorageRepository(ABC):
    """
    Unified interface for file storage operations.

    This interface defines the contract for physical file storage,
        allowing different implementations (e.g., local filesystem) without
        coupling the domain layer to infrastructure details.

    Contract Guarantees:
    - All methods are idempotent where applicable (e.g., delete, exists)
    - Implementations must handle errors gracefully
    - File paths are relative to the storage root
    - Binary content is handled via BinaryIO for streaming support

    Implementation Requirements:
    - save(): Must create parent directories if needed
    - get(): Must return None for non-existent files (no exceptions)
    - delete(): Must succeed even if file doesn't exist (idempotent)
    - exists(): Must never raise exceptions for invalid paths
    - get_size(): Must return None for non-existent files or directories

    Thread Safety:
    - Implementations should be thread-safe for concurrent operations
    - Multiple reads are safe; write operations should use appropriate locking
    """

    @abstractmethod
    def save(self, file_path: str, content: BinaryIO) -> bool:
        """
        Save file content to storage.

        Stores the binary content at the specified path. If the file already
        exists, it will be overwritten. Parent directories are created automatically.

        Args:
            file_path: Relative path for the file (e.g., 'videos/abc123/video.mp4')
            content: Binary file content as a file-like object (BinaryIO)

        Returns:
            True if the file was successfully saved, False otherwise

        Raises:
            PermissionError: If there are insufficient permissions to write
            IOError: If there are I/O errors during the operation
            ValueError: If file_path is empty or invalid

        Example:
            >>> with open('/tmp/video.mp4', 'rb') as f:
            ...     repository.save('downloads/video.mp4', f)
            True

        Notes:
            - The content stream position should be at the beginning
            - Implementations should handle large files efficiently (streaming)
            - Atomic writes are preferred where possible
        """
        pass  # pragma: no cover

    @abstractmethod
    def get(self, file_path: str) -> Optional[BinaryIO]:
        """
        Retrieve file content from storage.

        Returns a binary stream of the file content. The caller is responsible
        for closing the stream after use.

        Args:
            file_path: Relative path to the file (e.g., 'downloads/video.mp4')

        Returns:
            Binary file content as BinaryIO if found, None if file doesn't exist

        Example:
            >>> content = repository.get('downloads/video.mp4')
            >>> if content:
            ...     data = content.read()
            ...     content.close()

        Notes:
            - Returns None instead of raising exceptions for missing files
            - Caller must close the returned stream to avoid resource leaks
            - Implementations should support efficient streaming for large files
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Removes the file at the specified path. This operation is idempotent -
        deleting a non-existent file returns True without error.

        Args:
            file_path: Relative path to the file (e.g., 'downloads/video.mp4')

        Returns:
            True if the file was deleted or didn't exist, False on failure

        Raises:
            PermissionError: If there are insufficient permissions to delete
            IOError: If there are I/O errors during the operation

        Example:
            >>> repository.delete('downloads/video.mp4')
            True
            >>> repository.delete('downloads/nonexistent.mp4')  # Still returns True
            True

        Notes:
            - Idempotent operation (safe to call multiple times)
            - Does not delete directories, only files
            - Parent directories are not removed even if empty
        """
        pass  # pragma: no cover

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists at the specified path.

        Verifies file existence without raising exceptions. This method
        should never fail - invalid paths return False.

        Args:
            file_path: Relative path to check (e.g., 'downloads/video.mp4')

        Returns:
            True if the file exists, False otherwise

        Example:
            >>> repository.exists('downloads/video.mp4')
            True
            >>> repository.exists('downloads/missing.mp4')
            False
            >>> repository.exists('')  # Invalid path
            False

        Notes:
            - Never raises exceptions (returns False for errors)
            - Checks file existence only (not directories)
            - Empty or invalid paths return False
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_size(self, file_path: str) -> Optional[int]:
        """
        Get the size of a file in bytes.

        Returns the file size without reading the entire file content.
        Useful for validation and progress tracking.

        Args:
            file_path: Relative path to the file (e.g., 'downloads/video.mp4')

        Returns:
            File size in bytes if the file exists, None if file doesn't exist
            or if there's an error retrieving the size

        Example:
            >>> repository.get_size('downloads/video.mp4')
            15728640  # 15 MB in bytes
            >>> repository.get_size('downloads/missing.mp4')
            None

        Notes:
            - Returns None for non-existent files (not an error)
            - Returns None for directories
            - Efficient operation (doesn't read file content)
        """
        pass  # pragma: no cover
