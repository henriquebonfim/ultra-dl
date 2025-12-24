"""
File Storage Repositories

Repository interface for file metadata persistence.
Concrete implementations are in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import DownloadedFile


class FileRepository(ABC):
    """Abstract repository interface for file metadata persistence."""

    @abstractmethod
    def save(self, file: DownloadedFile) -> bool:
        """
        Save file metadata.

        Args:
            file: DownloadedFile to save

        Returns:
            True if successful, False otherwise
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_by_token(self, token: str) -> Optional[DownloadedFile]:
        """
        Retrieve file by token.

        Args:
            token: File access token

        Returns:
            DownloadedFile if found, None otherwise
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_by_job_id(self, job_id: str) -> Optional[DownloadedFile]:
        """
        Retrieve file by job ID.

        Args:
            job_id: Job identifier

        Returns:
            DownloadedFile if found, None otherwise
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete(self, token: str) -> bool:
        """
        Delete file metadata.

        Args:
            token: File access token

        Returns:
            True if deleted, False otherwise
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_expired_files(self) -> List[DownloadedFile]:
        """
        Get list of expired files.

        Returns:
            List of expired DownloadedFile instances
        """
        pass  # pragma: no cover

    @abstractmethod
    def exists(self, token: str) -> bool:
        """
        Check if file metadata exists.

        Args:
            token: File access token

        Returns:
            True if exists, False otherwise
        """
        pass  # pragma: no cover
