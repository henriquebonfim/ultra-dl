"""
Mock Repository Implementations

In-memory mock implementations of repository interfaces for unit testing.
Provides realistic behavior with inspection methods for test assertions.

Requirements: 7.3
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.domain.job_management.entities import DownloadJob, JobArchive
from src.domain.job_management.repositories import IJobArchiveRepository, JobRepository
from src.domain.job_management.value_objects import JobProgress, JobStatus


class MockJobRepository(JobRepository):
    """
    In-memory mock implementation of JobRepository.

    Provides realistic behavior for unit testing with inspection methods
    for verifying repository interactions.
    """

    def __init__(self):
        self._storage: Dict[str, DownloadJob] = {}
        self._call_history: List[Dict[str, Any]] = []

    def save(self, job: DownloadJob) -> bool:
        """Save or update a job in memory."""
        self._call_history.append({"method": "save", "args": {"job_id": job.job_id}})
        self._storage[job.job_id] = job
        return True

    def get(self, job_id: str) -> Optional[DownloadJob]:
        """Retrieve a job by ID."""
        self._call_history.append({"method": "get", "args": {"job_id": job_id}})
        return self._storage.get(job_id)

    def delete(self, job_id: str) -> bool:
        """Delete a job from storage."""
        self._call_history.append({"method": "delete", "args": {"job_id": job_id}})
        if job_id in self._storage:
            del self._storage[job_id]
            return True
        return False

    def update_progress(self, job_id: str, progress: JobProgress) -> bool:
        """Atomically update job progress."""
        self._call_history.append(
            {
                "method": "update_progress",
                "args": {"job_id": job_id, "progress": progress},
            }
        )
        job = self._storage.get(job_id)
        if job:
            job.progress = progress
            job.updated_at = datetime.utcnow()
            return True
        return False

    def update_status(
        self, job_id: str, status: JobStatus, error_message: Optional[str] = None
    ) -> bool:
        """Atomically update job status."""
        self._call_history.append(
            {
                "method": "update_status",
                "args": {
                    "job_id": job_id,
                    "status": status,
                    "error_message": error_message,
                },
            }
        )
        job = self._storage.get(job_id)
        if job:
            job.status = status
            if error_message:
                job.error_message = error_message
            job.updated_at = datetime.utcnow()
            return True
        return False

    def get_expired_jobs(self, expiration_time: timedelta) -> List[str]:
        """Get list of expired job IDs."""
        self._call_history.append(
            {"method": "get_expired_jobs", "args": {"expiration_time": expiration_time}}
        )
        cutoff = datetime.utcnow() - expiration_time
        return [
            job_id for job_id, job in self._storage.items() if job.updated_at < cutoff
        ]

    def exists(self, job_id: str) -> bool:
        """Check if job exists."""
        self._call_history.append({"method": "exists", "args": {"job_id": job_id}})
        return job_id in self._storage

    def get_many(self, job_ids: List[str]) -> List[DownloadJob]:
        """Retrieve multiple jobs by their IDs."""
        self._call_history.append({"method": "get_many", "args": {"job_ids": job_ids}})
        return [self._storage[job_id] for job_id in job_ids if job_id in self._storage]

    def save_many(self, jobs: List[DownloadJob]) -> bool:
        """Save multiple jobs atomically."""
        self._call_history.append(
            {"method": "save_many", "args": {"job_ids": [j.job_id for j in jobs]}}
        )
        for job in jobs:
            self._storage[job.job_id] = job
        return True

    def find_by_status(self, status: JobStatus, limit: int = 100) -> List[DownloadJob]:
        """Find jobs by status."""
        self._call_history.append(
            {"method": "find_by_status", "args": {"status": status, "limit": limit}}
        )
        matching = [job for job in self._storage.values() if job.status == status]
        return matching[:limit]

    # Inspection methods for testing
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all method calls for verification."""
        return self._call_history.copy()

    def clear_call_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()

    def get_all_jobs(self) -> Dict[str, DownloadJob]:
        """Get all stored jobs for inspection."""
        return self._storage.copy()

    def clear(self) -> None:
        """Clear all stored data and call history."""
        self._storage.clear()
        self._call_history.clear()


class MockArchiveRepository(IJobArchiveRepository):
    """
    In-memory mock implementation of IJobArchiveRepository.

    Provides realistic behavior for unit testing with inspection methods.
    """

    def __init__(self):
        self._storage: Dict[str, JobArchive] = {}
        self._call_history: List[Dict[str, Any]] = []

    def save(self, archive: JobArchive) -> bool:
        """Save archived job metadata."""
        self._call_history.append(
            {"method": "save", "args": {"job_id": archive.job_id}}
        )
        self._storage[archive.job_id] = archive
        return True

    def get(self, job_id: str) -> Optional[JobArchive]:
        """Retrieve archived job by ID."""
        self._call_history.append({"method": "get", "args": {"job_id": job_id}})
        return self._storage.get(job_id)

    def get_by_date_range(self, start: datetime, end: datetime) -> List[JobArchive]:
        """Query archives by date range."""
        self._call_history.append(
            {"method": "get_by_date_range", "args": {"start": start, "end": end}}
        )
        return [
            archive
            for archive in self._storage.values()
            if start <= archive.archived_at <= end
        ]

    def count_by_status(self, status: str) -> int:
        """Count archived jobs by status."""
        self._call_history.append(
            {"method": "count_by_status", "args": {"status": status}}
        )
        return sum(1 for archive in self._storage.values() if archive.status == status)

    # Inspection methods
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all method calls."""
        return self._call_history.copy()

    def clear(self) -> None:
        """Clear all stored data and call history."""
        self._storage.clear()
        self._call_history.clear()


class MockFileRepository:
    """
    In-memory mock implementation of FileRepository interface.

    Simulates file metadata storage with TTL expiration support.
    Implements the FileRepository interface from domain layer.
    """

    def __init__(self):
        self._storage_by_token: Dict[str, Any] = {}  # token -> DownloadedFile
        self._storage_by_job: Dict[str, str] = {}  # job_id -> token
        self._call_history: List[Dict[str, Any]] = []

    def save(self, file: Any) -> bool:
        """
        Save file metadata.

        Args:
            file: DownloadedFile entity to save

        Returns:
            True if successful
        """
        self._call_history.append(
            {
                "method": "save",
                "args": {"token": str(file.token), "job_id": file.job_id},
            }
        )
        token_str = str(file.token)
        self._storage_by_token[token_str] = file
        self._storage_by_job[file.job_id] = token_str
        return True

    def get_by_token(self, token: str) -> Optional[Any]:
        """
        Retrieve file by token.

        Args:
            token: File access token

        Returns:
            DownloadedFile if found, None otherwise
        """
        self._call_history.append({"method": "get_by_token", "args": {"token": token}})
        return self._storage_by_token.get(token)

    def get_by_job_id(self, job_id: str) -> Optional[Any]:
        """
        Retrieve file by job ID.

        Args:
            job_id: Job identifier

        Returns:
            DownloadedFile if found, None otherwise
        """
        self._call_history.append(
            {"method": "get_by_job_id", "args": {"job_id": job_id}}
        )
        token = self._storage_by_job.get(job_id)
        if token:
            return self._storage_by_token.get(token)
        return None

    def delete(self, token: str) -> bool:
        """
        Delete file metadata by token.

        Args:
            token: File access token

        Returns:
            True if deleted, False otherwise
        """
        self._call_history.append({"method": "delete", "args": {"token": token}})
        if token in self._storage_by_token:
            file = self._storage_by_token[token]
            del self._storage_by_token[token]
            if file.job_id in self._storage_by_job:
                del self._storage_by_job[file.job_id]
            return True
        return False

    def get_expired_files(self) -> List[Any]:
        """
        Get list of expired files.

        Returns:
            List of expired DownloadedFile instances
        """
        self._call_history.append({"method": "get_expired_files", "args": {}})
        now = datetime.utcnow()
        return [
            file for file in self._storage_by_token.values() if file.expires_at < now
        ]

    def exists(self, token: str) -> bool:
        """
        Check if file metadata exists.

        Args:
            token: File access token

        Returns:
            True if exists, False otherwise
        """
        self._call_history.append({"method": "exists", "args": {"token": token}})
        return token in self._storage_by_token

    # Inspection methods
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all method calls."""
        return self._call_history.copy()

    def get_all_files(self) -> Dict[str, Any]:
        """Get all stored files for inspection."""
        return self._storage_by_token.copy()

    def clear(self) -> None:
        """Clear all stored data and call history."""
        self._storage_by_token.clear()
        self._storage_by_job.clear()
        self._call_history.clear()


class MockStorageRepository:
    """
    In-memory mock implementation of IFileStorageRepository interface.

    Simulates file storage operations without actual file system access.
    Implements the IFileStorageRepository interface from domain layer.
    """

    def __init__(self):
        self._storage: Dict[str, bytes] = {}
        self._call_history: List[Dict[str, Any]] = []
        # Add base_path for local storage compatibility
        from pathlib import Path

        self.base_path = Path("/mock/storage")

    def save(self, file_path: str, content: Any) -> bool:
        """
        Save file content to storage.

        Args:
            file_path: Relative path for the file
            content: Binary file content as BinaryIO

        Returns:
            True if successful
        """
        self._call_history.append({"method": "save", "args": {"file_path": file_path}})
        # Handle both BinaryIO and bytes
        if hasattr(content, "read"):
            data = content.read()
        else:
            data = content
        self._storage[file_path] = data
        return True

    def get(self, file_path: str) -> Optional[Any]:
        """
        Retrieve file content from storage.

        Args:
            file_path: Relative path to the file

        Returns:
            Binary file content as BytesIO if found, None otherwise
        """
        self._call_history.append({"method": "get", "args": {"file_path": file_path}})
        content = self._storage.get(file_path)
        if content is not None:
            from io import BytesIO

            return BytesIO(content)
        return None

    def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Relative path to the file

        Returns:
            True if deleted or didn't exist
        """
        self._call_history.append(
            {"method": "delete", "args": {"file_path": file_path}}
        )
        if file_path in self._storage:
            del self._storage[file_path]
        return True  # Idempotent - always returns True

    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            file_path: Relative path to check

        Returns:
            True if file exists
        """
        self._call_history.append(
            {"method": "exists", "args": {"file_path": file_path}}
        )
        return file_path in self._storage

    def get_size(self, file_path: str) -> Optional[int]:
        """
        Get the size of a file in bytes.

        Args:
            file_path: Relative path to the file

        Returns:
            File size in bytes if exists, None otherwise
        """
        self._call_history.append(
            {"method": "get_size", "args": {"file_path": file_path}}
        )
        content = self._storage.get(file_path)
        if content is not None:
            return len(content)
        return None

    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for content access.

        Args:
            path: Path to the file
            expiration: URL expiration time in seconds

        Returns:
            Mock signed URL
        """
        self._call_history.append(
            {
                "method": "generate_signed_url",
                "args": {"path": path, "expiration": expiration},
            }
        )
        return f"https://storage.example.com/{path}?token=mock_signed_token&expires={expiration}"

    # Inspection methods
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all method calls."""
        return self._call_history.copy()

    def get_stored_content(self) -> Dict[str, bytes]:
        """Get all stored content for inspection."""
        return self._storage.copy()

    def clear(self) -> None:
        """Clear all stored data and call history."""
        self._storage.clear()
        self._call_history.clear()


class MockMetadataExtractor:
    """
    Mock implementation of video metadata extractor.

    Provides deterministic behavior for testing without actual yt-dlp calls.
    """

    def __init__(self):
        self._call_history: List[Dict[str, Any]] = []
        self._metadata_response: Dict[str, Any] = {
            "title": "Test Video Title",
            "duration": 180,
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "uploader": "Test Channel",
            "view_count": 1000000,
        }
        self._formats_response: List[Dict[str, Any]] = [
            {
                "format_id": "137",
                "ext": "mp4",
                "resolution": "1920x1080",
                "vcodec": "avc1",
                "acodec": "none",
                "filesize": 50000000,
            },
            {
                "format_id": "140",
                "ext": "m4a",
                "resolution": "audio only",
                "vcodec": "none",
                "acodec": "mp4a",
                "filesize": 5000000,
            },
            {
                "format_id": "best",
                "ext": "mp4",
                "resolution": "1920x1080",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "filesize": 55000000,
            },
        ]
        self._should_fail = False
        self._fail_message = "Extraction failed"

    def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Extract video metadata."""
        self._call_history.append({"method": "extract_metadata", "args": {"url": url}})
        if self._should_fail:
            raise Exception(self._fail_message)
        return self._metadata_response.copy()

    def extract_formats(self, url: str) -> List[Dict[str, Any]]:
        """Extract available formats."""
        self._call_history.append({"method": "extract_formats", "args": {"url": url}})
        if self._should_fail:
            raise Exception(self._fail_message)
        return self._formats_response.copy()

    # Configuration methods for testing
    def set_metadata_response(self, metadata: Dict[str, Any]) -> None:
        """Set custom metadata response."""
        self._metadata_response = metadata

    def set_formats_response(self, formats: List[Dict[str, Any]]) -> None:
        """Set custom formats response."""
        self._formats_response = formats

    def set_should_fail(
        self, should_fail: bool, message: str = "Extraction failed"
    ) -> None:
        """Configure extractor to fail on next call."""
        self._should_fail = should_fail
        self._fail_message = message

    # Inspection methods
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all method calls."""
        return self._call_history.copy()

    def clear(self) -> None:
        """Clear call history and reset configuration."""
        self._call_history.clear()
        self._should_fail = False
