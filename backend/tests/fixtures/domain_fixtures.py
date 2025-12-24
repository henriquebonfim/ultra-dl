"""
Domain Entity Factories

Factory functions for creating domain entities with sensible defaults.
Supports customization via keyword arguments for flexible test data creation.

Requirements: 7.1
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Union

from src.domain.job_management.entities import DownloadJob, JobArchive
from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.video_processing.value_objects import FormatId
from src.domain.video_processing.entities import VideoMetadata, VideoFormat
from src.domain.file_storage.value_objects import DownloadToken
from src.domain.file_storage.entities import DownloadedFile


def create_download_job(
    job_id: Optional[str] = None,
    url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    format_id: Union[str, FormatId] = "best",
    status: JobStatus = JobStatus.PENDING,
    progress: Optional[JobProgress] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    error_category: Optional[str] = None,
    download_url: Optional[str] = None,
    download_token: Optional[DownloadToken] = None,
    expire_at: Optional[datetime] = None,
) -> DownloadJob:
    """
    Create a DownloadJob entity with sensible defaults.
    
    Args:
        job_id: Unique job identifier (auto-generated if not provided)
        url: YouTube URL to download
        format_id: Format ID string or FormatId (will be converted to FormatId if string)
        status: Job status (default: PENDING)
        progress: Job progress (default: initial progress)
        created_at: Creation timestamp (default: now)
        updated_at: Last update timestamp (default: now)
        error_message: Error message for failed jobs
        error_category: Error category for failed jobs
        download_url: URL to download completed file
        download_token: Token for file access
        expire_at: When the download expires
        
    Returns:
        DownloadJob instance with specified or default values
    """
    now = datetime.utcnow()
    
    # Convert string to FormatId if needed
    format_id_vo = FormatId(format_id) if isinstance(format_id, str) else format_id
    
    return DownloadJob(
        job_id=job_id or str(uuid.uuid4()),
        url=url,
        format_id=format_id_vo,
        status=status,
        progress=progress or JobProgress.initial(),
        created_at=created_at or now,
        updated_at=updated_at or now,
        error_message=error_message,
        error_category=error_category,
        download_url=download_url,
        download_token=download_token,
        expire_at=expire_at,
    )


def create_job_archive(
    job_id: Optional[str] = None,
    url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    format_id: str = "best",
    status: str = "completed",
    created_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    archived_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    error_category: Optional[str] = None,
    download_token: Optional[str] = None,
) -> JobArchive:
    """
    Create a JobArchive entity with sensible defaults.
    
    Args:
        job_id: Unique job identifier (auto-generated if not provided)
        url: YouTube URL that was downloaded
        format_id: Format ID string
        status: Final job status (completed/failed)
        created_at: Original job creation timestamp
        completed_at: When the job completed
        archived_at: When the job was archived
        error_message: Error message for failed jobs
        error_category: Error category for failed jobs
        download_token: Token that was used for file access
        
    Returns:
        JobArchive instance with specified or default values
    """
    now = datetime.utcnow()
    
    return JobArchive(
        job_id=job_id or str(uuid.uuid4()),
        url=url,
        format_id=format_id,
        status=status,
        created_at=created_at or (now - timedelta(hours=1)),
        completed_at=completed_at or now,
        archived_at=archived_at or now,
        error_message=error_message,
        error_category=error_category,
        download_token=download_token,
    )


def create_downloaded_file(
    file_path: Optional[str] = None,
    token: Optional[DownloadToken] = None,
    job_id: Optional[str] = None,
    filename: str = "test_video.mp4",
    expires_at: Optional[datetime] = None,
    created_at: Optional[datetime] = None,
    filesize: Optional[int] = 1024 * 1024,  # 1MB default
    ttl_minutes: int = 10,
) -> DownloadedFile:
    """
    Create a DownloadedFile entity with sensible defaults.
    
    Args:
        file_path: Path to the downloaded file
        token: DownloadToken for file access (auto-generated if not provided)
        job_id: Associated job identifier (auto-generated if not provided)
        filename: Name of the downloaded file
        expires_at: When the file expires (calculated from ttl_minutes if not provided)
        created_at: When the file was created (default: now)
        filesize: File size in bytes
        ttl_minutes: Time to live in minutes (used if expires_at not provided)
        
    Returns:
        DownloadedFile entity instance
    """
    now = datetime.utcnow()
    job_id = job_id or str(uuid.uuid4())
    
    return DownloadedFile(
        file_path=file_path or f"/downloads/{job_id}/{filename}",
        token=token or DownloadToken.generate(),
        job_id=job_id,
        filename=filename,
        expires_at=expires_at or (now + timedelta(minutes=ttl_minutes)),
        created_at=created_at or now,
        filesize=filesize,
    )


def create_video_metadata(
    video_id: str = "dQw4w9WgXcQ",
    title: str = "Test Video Title",
    uploader: str = "Test Channel",
    duration: int = 180,
    thumbnail: Optional[str] = None,
    url: Optional[str] = None,
    extracted_at: Optional[datetime] = None,
) -> VideoMetadata:
    """
    Create a VideoMetadata entity with sensible defaults.
    
    Args:
        video_id: YouTube video ID
        title: Video title
        uploader: Channel/uploader name
        duration: Video duration in seconds
        thumbnail: Thumbnail URL
        url: Video URL
        extracted_at: When metadata was extracted
        
    Returns:
        VideoMetadata entity instance
    """
    return VideoMetadata(
        id=video_id,
        title=title,
        uploader=uploader,
        duration=duration,
        thumbnail=thumbnail or f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        url=url or f"https://www.youtube.com/watch?v={video_id}",
        extracted_at=extracted_at or datetime.utcnow(),
    )


def create_video_format(
    format_id: str = "137",
    extension: str = "mp4",
    resolution: str = "1920x1080",
    height: int = 1080,
    width: Optional[int] = 1920,
    filesize: Optional[int] = 50000000,
    video_codec: Optional[str] = "avc1",
    audio_codec: Optional[str] = "mp4a",
    quality_label: Optional[str] = None,
    format_note: Optional[str] = None,
) -> VideoFormat:
    """
    Create a VideoFormat entity with sensible defaults.
    
    Args:
        format_id: Format identifier
        extension: File extension
        resolution: Resolution string
        height: Video height in pixels
        width: Video width in pixels
        filesize: File size in bytes
        video_codec: Video codec name
        audio_codec: Audio codec name
        quality_label: Quality label (e.g., "Great", "Good")
        format_note: Additional format notes
        
    Returns:
        VideoFormat entity instance
    """
    return VideoFormat(
        format_id=format_id,
        extension=extension,
        resolution=resolution,
        height=height,
        width=width,
        filesize=filesize,
        video_codec=video_codec,
        audio_codec=audio_codec,
        quality_label=quality_label,
        format_note=format_note,
    )

