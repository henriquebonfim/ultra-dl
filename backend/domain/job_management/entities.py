"""
Job Management Entities

Domain entities for download job management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .value_objects import JobProgress, JobStatus
from ..video_processing.value_objects import FormatId
from ..file_storage.value_objects import DownloadToken

if TYPE_CHECKING:
    from ..events import JobStartedEvent, JobCompletedEvent, JobFailedEvent
else:
    # Import at runtime to avoid circular import
    def _import_events():
        from ..events import JobStartedEvent, JobCompletedEvent, JobFailedEvent
        return JobStartedEvent, JobCompletedEvent, JobFailedEvent


@dataclass
class DownloadJob:
    """
    Entity representing a download job.

    Manages job lifecycle with status transitions and progress tracking.
    """

    job_id: str
    url: str
    format_id: FormatId
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    download_url: Optional[str] = None
    download_token: Optional[DownloadToken] = None
    expire_at: Optional[datetime] = None

    @classmethod
    def create(cls, url: str, format_id: str) -> "DownloadJob":
        """
        Factory method to create a new download job.

        Args:
            url: YouTube URL
            format_id: Format ID to download (string will be converted to FormatId)

        Returns:
            New DownloadJob instance
        """
        now = datetime.utcnow()
        job_id = str(uuid.uuid4())

        # Convert string to FormatId value object
        format_id_vo = FormatId(format_id) if isinstance(format_id, str) else format_id

        return cls(
            job_id=job_id,
            url=url,
            format_id=format_id_vo,
            status=JobStatus.PENDING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now,
        )

    def start(self) -> Optional['JobStartedEvent']:
        """
        Transition job to processing state.

        If the job is already processing, this method is idempotent
        and does nothing.

        Returns:
            JobStartedEvent if state transition occurred, None if already processing

        Raises:
            ValueError: If job is not in pending or processing state
        """
        if self.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            raise ValueError(f"Cannot start job in {self.status.value} state")

        if self.status == JobStatus.PENDING:
            self.status = JobStatus.PROCESSING
            self.progress = JobProgress.metadata_extraction()
            self.updated_at = datetime.utcnow()
            
            # Return event for state transition
            JobStartedEvent, _, _ = _import_events()
            return JobStartedEvent(
                aggregate_id=self.job_id,
                occurred_at=self.updated_at,
                url=self.url,
                format_id=str(self.format_id)
            )
        
        # Already processing, no event needed
        return None

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
        download_token: Optional[DownloadToken] = None,
        expire_at: Optional[datetime] = None,
    ) -> 'JobCompletedEvent':
        """
        Mark job as completed.

        Args:
            download_url: URL to download the file
            download_token: Token for file access (DownloadToken value object)
            expire_at: When the download URL expires

        Returns:
            JobCompletedEvent indicating successful completion

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
        
        # Return event for state transition
        _, JobCompletedEvent, _ = _import_events()
        return JobCompletedEvent(
            aggregate_id=self.job_id,
            occurred_at=self.updated_at,
            download_url=download_url or "",
            expire_at=expire_at or self.updated_at
        )

    def fail(self, error_message: str, error_category: Optional[str] = None) -> 'JobFailedEvent':
        """
        Mark job as failed.

        Args:
            error_message: Error description
            error_category: Optional error category for tracking

        Returns:
            JobFailedEvent indicating failure
        """
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.error_category = error_category
        self.updated_at = datetime.utcnow()
        
        # Return event for state transition
        _, _, JobFailedEvent = _import_events()
        return JobFailedEvent(
            aggregate_id=self.job_id,
            occurred_at=self.updated_at,
            error_message=error_message,
            error_category=error_category or "UNKNOWN"
        )

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
            "format_id": str(self.format_id),
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
            "error_category": self.error_category,
            "download_url": self.download_url,
            "download_token": str(self.download_token) if self.download_token else None,
            "expire_at": self.expire_at.isoformat() if self.expire_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadJob":
        """Create DownloadJob from dictionary."""
        # Convert string format_id to FormatId value object
        format_id_str = data["format_id"]
        format_id_vo = FormatId(format_id_str)
        
        # Convert string download_token to DownloadToken value object if present
        download_token_str = data.get("download_token")
        download_token_vo = DownloadToken(download_token_str) if download_token_str else None
        
        return cls(
            job_id=data["job_id"],
            url=data["url"],
            format_id=format_id_vo,
            status=JobStatus(data["status"]),
            progress=JobProgress.from_dict(data["progress"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
            error_category=data.get("error_category"),
            download_url=data.get("download_url"),
            download_token=download_token_vo,
            expire_at=(
                datetime.fromisoformat(data["expire_at"])
                if data.get("expire_at")
                else None
            ),
        )
