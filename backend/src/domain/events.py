"""
Domain Events

Immutable records of significant state changes in the domain.
Events decouple side effects (WebSocket notifications, logging) from core business logic.
"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from .job_management.value_objects import JobProgress


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    Base class for all domain events.
    
    Domain events are immutable records of something that happened in the domain.
    They enable decoupling of side effects from core business logic.
    
    Attributes:
        aggregate_id: ID of the aggregate that generated the event (e.g., job_id)
        occurred_at: Timestamp when the event occurred
    """
    aggregate_id: str
    occurred_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.__class__.__name__,
            "aggregate_id": self.aggregate_id,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class JobStartedEvent(DomainEvent):
    """
    Event emitted when a download job starts processing.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the job started
        url: YouTube URL being downloaded
        format_id: Format ID selected for download
    """
    url: str
    format_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "url": self.url,
            "format_id": self.format_id,
        })
        return base_dict


@dataclass(frozen=True)
class JobProgressUpdatedEvent(DomainEvent):
    """
    Event emitted when a download job's progress is updated.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the progress was updated
        progress: Current progress information
    """
    progress: JobProgress
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "progress": self.progress.to_dict(),
        })
        return base_dict


@dataclass(frozen=True)
class JobCompletedEvent(DomainEvent):
    """
    Event emitted when a download job completes successfully.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the job completed
        download_url: URL to download the file
        expire_at: When the download URL expires
    """
    download_url: str
    expire_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "download_url": self.download_url,
            "expire_at": self.expire_at.isoformat(),
        })
        return base_dict


@dataclass(frozen=True)
class JobFailedEvent(DomainEvent):
    """
    Event emitted when a download job fails.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the job failed
        error_message: Human-readable error message
        error_category: Error category for tracking and analytics
    """
    error_message: str
    error_category: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "error_message": self.error_message,
            "error_category": self.error_category,
        })
        return base_dict


@dataclass(frozen=True)
class VideoMetadataExtractedEvent(DomainEvent):
    """
    Event emitted when video metadata is successfully extracted.
    
    Attributes:
        aggregate_id: Video ID or job ID
        occurred_at: When the metadata was extracted
        video_id: YouTube video ID
        title: Video title
        duration: Video duration in seconds
    """
    video_id: str
    title: str
    duration: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "video_id": self.video_id,
            "title": self.title,
            "duration": self.duration,
        })
        return base_dict


@dataclass(frozen=True)
class MetadataExtractionFailedEvent(DomainEvent):
    """
    Event emitted when metadata extraction fails.
    
    Attributes:
        aggregate_id: Job ID or URL identifier
        occurred_at: When the extraction failed
        url: YouTube URL that failed
        error_message: Human-readable error message
    """
    url: str
    error_message: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "url": self.url,
            "error_message": self.error_message,
        })
        return base_dict


@dataclass(frozen=True)
class FormatExtractionCompletedEvent(DomainEvent):
    """
    Event emitted when format extraction completes.
    
    Attributes:
        aggregate_id: Video ID or job ID
        occurred_at: When the extraction completed
        url: YouTube URL
        format_count: Number of formats extracted
    """
    url: str
    format_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "url": self.url,
            "format_count": self.format_count,
        })
        return base_dict


@dataclass(frozen=True)
class VideoDownloadStartedEvent(DomainEvent):
    """
    Event emitted when video download starts.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the download started
        video_id: YouTube video ID
        format_id: Format ID being downloaded
    """
    video_id: str
    format_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "video_id": self.video_id,
            "format_id": self.format_id,
        })
        return base_dict


@dataclass(frozen=True)
class VideoDownloadProgressEvent(DomainEvent):
    """
    Event emitted when video download progress is updated.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the progress was updated
        video_id: YouTube video ID
        downloaded_bytes: Number of bytes downloaded
        total_bytes: Total bytes to download
        percentage: Download percentage (0-100)
    """
    video_id: str
    downloaded_bytes: int
    total_bytes: int
    percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "video_id": self.video_id,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "percentage": self.percentage,
        })
        return base_dict


@dataclass(frozen=True)
class VideoDownloadCompletedEvent(DomainEvent):
    """
    Event emitted when video download completes successfully.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the download completed
        video_id: YouTube video ID
        file_path: Path to the downloaded file
        file_size: Size of the downloaded file in bytes
    """
    video_id: str
    file_path: str
    file_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "video_id": self.video_id,
            "file_path": self.file_path,
            "file_size": self.file_size,
        })
        return base_dict


@dataclass(frozen=True)
class VideoDownloadFailedEvent(DomainEvent):
    """
    Event emitted when video download fails.
    
    Attributes:
        aggregate_id: Job ID
        occurred_at: When the download failed
        video_id: YouTube video ID
        error_message: Human-readable error message
    """
    video_id: str
    error_message: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "video_id": self.video_id,
            "error_message": self.error_message,
        })
        return base_dict


@dataclass(frozen=True)
class FileCleanupFailedEvent(DomainEvent):
    """
    Event emitted when file cleanup fails.
    
    Attributes:
        aggregate_id: File token
        occurred_at: When the cleanup failed
        error_message: Human-readable error message
    """
    error_message: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "error_message": self.error_message,
        })
        return base_dict
