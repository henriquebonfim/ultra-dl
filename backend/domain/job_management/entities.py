"""
Job Management Entities

Domain entities for download job management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .value_objects import JobProgress, JobStatus


@dataclass
class DownloadJob:
    """
    Entity representing a download job.

    Manages job lifecycle with status transitions and progress tracking.
    """

    job_id: str
    url: str
    format_id: str
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    download_url: Optional[str] = None
    download_token: Optional[str] = None
    expire_at: Optional[datetime] = None

    @classmethod
    def create(cls, url: str, format_id: str) -> "DownloadJob":
        """
        Factory method to create a new download job.

        Args:
            url: YouTube URL
            format_id: Format ID to download

        Returns:
            New DownloadJob instance
        """
        now = datetime.utcnow()
        job_id = str(uuid.uuid4())

        return cls(
            job_id=job_id,
            url=url,
            format_id=format_id,
            status=JobStatus.PENDING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now,
        )

    def start(self) -> None:
        """
        Transition job to processing state.

        If the job is already processing, this method is idempotent
        and does nothing.

        Raises:
            ValueError: If job is not in pending or processing state
        """
        if self.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            raise ValueError(f"Cannot start job in {self.status.value} state")

        if self.status == JobStatus.PENDING:
            self.status = JobStatus.PROCESSING
            self.progress = JobProgress.metadata_extraction()
            self.updated_at = datetime.utcnow()

    def update_progress(self, progress: JobProgress) -> None:
        """
        Update job progress.

        Args:
            progress: New progress information

        Raises:
            ValueError: If job is not in processing state
        """
        if self.status != JobStatus.PROCESSING:
            raise ValueError(
                f"Cannot update progress for job in {self.status.value} state"
            )

        self.progress = progress
        self.updated_at = datetime.utcnow()

    def complete(
        self,
        download_url: Optional[str] = None,
        download_token: Optional[str] = None,
        expire_at: Optional[datetime] = None,
    ) -> None:
        """
        Mark job as completed.

        Args:
            download_url: URL to download the file
            download_token: Token for file access
            expire_at: When the download URL expires

        Raises:
            ValueError: If job is not in processing state
        """
        if self.status != JobStatus.PROCESSING:
            raise ValueError(f"Cannot complete job in {self.status.value} state")

        self.status = JobStatus.COMPLETED
        self.progress = JobProgress.completed()
        self.download_url = download_url
        self.download_token = download_token
        self.expire_at = expire_at
        self.updated_at = datetime.utcnow()

    def fail(self, error_message: str, error_category: Optional[str] = None) -> None:
        """
        Mark job as failed.

        Args:
            error_message: Error description
            error_category: Optional error category for tracking
        """
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.error_category = error_category
        self.updated_at = datetime.utcnow()

    def is_terminal(self) -> bool:
        """Check if job is in terminal state (completed or failed)."""
        return self.status.is_terminal()

    def is_active(self) -> bool:
        """Check if job is actively processing."""
        return self.status.is_active()

    def to_dict(self) -> dict:
        """Convert job to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "url": self.url,
            "format_id": self.format_id,
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
            "error_category": self.error_category,
            "download_url": self.download_url,
            "download_token": self.download_token,
            "expire_at": self.expire_at.isoformat() if self.expire_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadJob":
        """Create DownloadJob from dictionary."""
        return cls(
            job_id=data["job_id"],
            url=data["url"],
            format_id=data["format_id"],
            status=JobStatus(data["status"]),
            progress=JobProgress.from_dict(data["progress"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
            error_category=data.get("error_category"),
            download_url=data.get("download_url"),
            download_token=data.get("download_token"),
            expire_at=(
                datetime.fromisoformat(data["expire_at"])
                if data.get("expire_at")
                else None
            ),
        )
