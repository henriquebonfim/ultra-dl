"""
Download Service

Application service that orchestrates the complete video download workflow.
Coordinates domain services and publishes domain events for state transitions.
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from domain.errors import ErrorCategory
from domain.events import (
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent,
    JobStartedEvent,
)
from domain.file_storage.services import FileManager
from domain.file_storage.storage_repository import IFileStorageRepository
from domain.job_management.services import JobManager
from domain.job_management.value_objects import JobProgress
from domain.video_processing.services import VideoProcessor
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, UnavailableVideoError

from .download_result import DownloadResult
from .event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class DownloadService:
    """
    Application service for orchestrating video download workflows.

    Coordinates JobManager, FileManager, VideoProcessor, and IFileStorageRepository
    to execute the complete download workflow. Publishes domain events at
    each state transition for decoupled side effects (WebSocket, logging).
    """

    def __init__(
        self,
        job_manager: JobManager,
        file_manager: FileManager,
        video_processor: VideoProcessor,
        storage_repository: IFileStorageRepository,
        event_publisher: EventPublisher,
    ):
        """
        Initialize Download Service with dependencies.

        Args:
            job_manager: Domain service for job lifecycle management
            file_manager: Domain service for file storage management
            video_processor: Domain service for video processing
            storage_repository: Infrastructure repository for file storage (IFileStorageRepository)
            event_publisher: Application service for event publishing
        """
        self.job_manager = job_manager
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.storage_repository = storage_repository
        self.event_publisher = event_publisher

        # Detect if using GCS based on environment
        self._is_gcs = self._detect_gcs_storage()

    def execute_download(
        self,
        job_id: str,
        url: str,
        format_id: str,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
    ) -> DownloadResult:
        """
        Execute complete video download workflow.

        Workflow:
        1. Start job and publish JobStartedEvent
        2. Download video with yt-dlp and progress callbacks
        3. Store file (GCS with local fallback)
        4. Generate download URL
        5. Complete job and publish JobCompletedEvent
        6. On error: categorize, fail job, publish JobFailedEvent

        Args:
            job_id: Unique job identifier
            url: YouTube URL to download
            format_id: Format ID for yt-dlp
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult with success/failure information
        """
        try:
            # Start job and publish event
            job = self._start_job(job_id, url, format_id)

            # Download video with progress tracking
            downloaded_file = self._download_video(
                job_id, url, format_id, progress_callback
            )

            # Store file and generate download URL
            download_url, expire_at = self._store_file(job_id, downloaded_file)

            # Complete job and publish event
            job = self._complete_job(job_id, download_url, expire_at)

            logger.info(f"Job {job_id} completed successfully")
            return DownloadResult.create_success(job, download_url)

        except Exception as e:
            # Handle error, categorize, and publish failure event
            return self._handle_error(job_id, e)

    def _start_job(self, job_id: str, url: str, format_id: str) -> Any:
        """
        Start job and publish JobStartedEvent.

        Args:
            job_id: Job identifier
            url: YouTube URL
            format_id: Format ID

        Returns:
            Started job
        """
        logger.info(f"Starting job {job_id} for URL: {url}, format: {format_id}")

        # Start job
        job = self.job_manager.start_job(job_id)

        # Publish JobStartedEvent
        event = JobStartedEvent(
            aggregate_id=job_id,
            occurred_at=datetime.utcnow(),
            url=url,
            format_id=format_id,
        )
        self.event_publisher.publish(event)

        return job

    def _download_video(
        self,
        job_id: str,
        url: str,
        format_id: str,
        progress_callback: Optional[Callable[[JobProgress], None]],
    ) -> Path:
        """
        Download video with yt-dlp and progress callbacks.

        Args:
            job_id: Job identifier
            url: YouTube URL
            format_id: Format ID
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file

        Raises:
            DownloadError, ExtractorError, UnavailableVideoError: yt-dlp errors
        """
        logger.info(f"Job {job_id}: Starting video download")

        # Create temporary directory for download
        temp_dir = Path(tempfile.gettempdir()) / "ultra-dl" / job_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        output_template = str(temp_dir / "%(title)s.%(ext)s")

        # Create progress hook
        def progress_hook(d: Dict[str, Any]) -> None:
            """yt-dlp progress hook for real-time updates."""
            try:
                status = d.get("status")

                if status == "downloading":
                    # Extract progress information
                    downloaded = d.get("downloaded_bytes", 0)
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                    # Calculate percentage
                    if total > 0:
                        percentage = min(int((downloaded / total) * 85) + 10, 95)
                    else:
                        percentage = 50

                    # Extract speed and ETA
                    speed = d.get("speed")
                    speed_str = None
                    if speed:
                        if speed > 1024 * 1024:
                            speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                        elif speed > 1024:
                            speed_str = f"{speed / 1024:.1f} KB/s"
                        else:
                            speed_str = f"{speed:.0f} B/s"

                    eta = d.get("eta")

                    # Create progress object
                    progress = JobProgress.downloading(
                        percentage=percentage, speed=speed_str, eta=eta
                    )

                    # Update job progress
                    self.job_manager.update_job_progress(job_id, progress)

                    # Publish progress event
                    event = JobProgressUpdatedEvent(
                        aggregate_id=job_id,
                        occurred_at=datetime.utcnow(),
                        progress=progress,
                    )
                    self.event_publisher.publish(event)

                    # Call external progress callback if provided
                    if progress_callback:
                        progress_callback(progress)

                elif status == "finished":
                    # Download finished, now processing
                    progress = JobProgress.processing(percentage=95)
                    self.job_manager.update_job_progress(job_id, progress)

                    # Publish progress event
                    event = JobProgressUpdatedEvent(
                        aggregate_id=job_id,
                        occurred_at=datetime.utcnow(),
                        progress=progress,
                    )
                    self.event_publisher.publish(event)

                    # Call external progress callback if provided
                    if progress_callback:
                        progress_callback(progress)

            except Exception as e:
                logger.warning(f"Error in progress hook for job {job_id}: {e}")

        # Configure yt-dlp options with performance optimizations
        ydl_opts = {
            "format": format_id,
            "outtmpl": output_template,
            "progress_hooks": [progress_hook],
            "quiet": False,
            "no_warnings": False,
            "extract_flat": False,
            # Performance optimizations
            "merge_output_format": "mp4",  # Efficient container format
            "prefer_ffmpeg": True,  # Use ffmpeg for faster processing
            # Network optimizations
            "socket_timeout": 30,  # 30s timeout for network operations
            "retries": 3,  # Retry failed downloads up to 3 times
            "fragment_retries": 3,  # Retry failed fragments up to 3 times
            "concurrent_fragment_downloads": 4,  # Download 4 fragments in parallel for DASH/HLS
            # Download optimizations
            "http_chunk_size": 10485760,  # 10MB chunks for better throughput
            "buffersize": 1024 * 1024,  # 1MB buffer size for I/O operations
            # Skip unnecessary operations
            "skip_download": False,  # We need the actual download
            "writesubtitles": False,  # Skip subtitle download for speed
            "writeautomaticsub": False,  # Skip auto-generated subtitles
            "writethumbnail": False,  # Skip thumbnail download
            "writedescription": False,  # Skip description file
            "writeinfojson": False,  # Skip info JSON file
            "writeannotations": False,  # Skip annotations
            # Metadata extraction optimization
            "extract_flat": False,  # Full extraction needed for download
            "lazy_playlist": True,  # Don't extract playlist info if not needed
        }

        # Download with yt-dlp
        with YoutubeDL(ydl_opts) as ydl:
            # Extract info first
            info = ydl.extract_info(url, download=False)

            # Update progress to show metadata extraction complete
            progress = JobProgress(percentage=10, phase="metadata extracted")
            self.job_manager.update_job_progress(job_id, progress)

            # Start actual download
            logger.info(f"Job {job_id}: Downloading video...")
            ydl.download([url])

            # Find downloaded file
            expected_filename = ydl.prepare_filename(info)
            downloaded_file = Path(expected_filename)

        # Verify file exists
        if not downloaded_file or not downloaded_file.exists():
            raise Exception(
                f"Downloaded file not found at expected location: {downloaded_file}"
            )

        logger.info(f"Job {job_id}: Download completed, file: {downloaded_file}")
        return downloaded_file

    def _detect_gcs_storage(self) -> bool:
        """
        Detect if using GCS storage based on environment configuration.

        Returns:
            True if using GCS, False for local storage
        """
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        return bool(gcs_bucket_name and gcs_bucket_name.strip())

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace unsafe characters
        safe_chars = "".join(
            c for c in filename if c.isalnum() or c in " .-_()"
        ).strip()

        # Ensure filename is not empty
        if not safe_chars:
            safe_chars = "download"

        return safe_chars

    def _store_file(self, job_id: str, downloaded_file: Path) -> tuple[str, datetime]:
        """
        Store file using IFileStorageRepository and generate download URL.

        Args:
            job_id: Job identifier
            downloaded_file: Path to downloaded file

        Returns:
            Tuple of (download_url, expire_at)
        """
        logger.info(f"Job {job_id}: Storing file")

        # Generate storage path
        safe_filename = self._sanitize_filename(downloaded_file.name)
        storage_path = f"{job_id}/{safe_filename}"

        # Read file content
        with open(downloaded_file, "rb") as f:
            content = BytesIO(f.read())

        # Save to storage using IFileStorageRepository
        self.storage_repository.save(storage_path, content)
        logger.info(f"Job {job_id}: File saved to storage at {storage_path}")

        # Generate download URL based on storage type
        ttl_minutes = 10
        expire_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

        if self._is_gcs:
            # GCS: Generate signed URL using GCSStorageRepository
            from infrastructure.gcs_storage_repository import GCSStorageRepository

            # Check if storage_repository is GCS instance
            if isinstance(self.storage_repository, GCSStorageRepository):
                download_url = self.storage_repository.generate_signed_url(
                    blob_name=storage_path, ttl_minutes=ttl_minutes
                )
                logger.info(f"Job {job_id}: Generated GCS signed URL")
            else:
                raise Exception(
                    "GCS storage expected but different repository provided"
                )

            # Delete local file after successful GCS upload
            try:
                downloaded_file.unlink()
                logger.info(f"Job {job_id}: Deleted local file after GCS upload")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to delete local file: {e}")
        else:
            # Local: Register file and generate download URL
            # For local storage, we need the full absolute path for file existence check
            full_file_path = str(self.storage_repository.base_path / storage_path)
            registered_file = self.file_manager.register_file(
                file_path=full_file_path,
                job_id=job_id,
                filename=downloaded_file.name,
                ttl_minutes=ttl_minutes,
            )

            # Generate download URL using the registered file's method
            download_url = registered_file.generate_download_url(
                base_url="/api/v1/downloads/file"
            )
            expire_at = registered_file.expires_at
            logger.info(f"Job {job_id}: Generated local download URL")

        return download_url, expire_at

    def _complete_job(self, job_id: str, download_url: str, expire_at: datetime) -> Any:
        """
        Complete job and publish JobCompletedEvent.

        Args:
            job_id: Job identifier
            download_url: URL to download the file
            expire_at: When the download URL expires

        Returns:
            Completed job
        """
        logger.info(f"Job {job_id}: Completing job")

        # Complete job
        job = self.job_manager.complete_job(
            job_id, download_url=download_url, expire_at=expire_at
        )

        # Publish JobCompletedEvent
        event = JobCompletedEvent(
            aggregate_id=job_id,
            occurred_at=datetime.utcnow(),
            download_url=download_url,
            expire_at=expire_at,
        )
        self.event_publisher.publish(event)

        return job

    def _categorize_download_error(self, exception: Exception) -> ErrorCategory:
        """
        Categorize download errors into error categories.

        This is an application-layer concern that maps infrastructure errors
        (yt-dlp exceptions) to user-friendly error categories.

        Args:
            exception: Exception that occurred during download

        Returns:
            ErrorCategory enum value representing the error type
        """
        # Import yt-dlp exceptions locally to avoid hard dependency
        try:
            from yt_dlp.utils import (
                DownloadError,
                ExtractorError,
                UnavailableVideoError,
            )
        except ImportError:
            logger.warning("yt-dlp not available for error categorization")
            return ErrorCategory.SYSTEM_ERROR

        # If it's not a yt-dlp error, return system error
        if not isinstance(
            exception, (DownloadError, ExtractorError, UnavailableVideoError)
        ):
            return ErrorCategory.SYSTEM_ERROR

        error_str = str(exception).lower()

        # Check for specific yt-dlp exception types
        if isinstance(exception, UnavailableVideoError):
            return ErrorCategory.VIDEO_UNAVAILABLE

        if isinstance(exception, ExtractorError):
            if "unsupported url" in error_str or "invalid url" in error_str:
                return ErrorCategory.INVALID_URL
            elif "private video" in error_str or "members-only" in error_str:
                return ErrorCategory.VIDEO_UNAVAILABLE
            elif "this video is not available" in error_str:
                return ErrorCategory.VIDEO_UNAVAILABLE
            else:
                return ErrorCategory.DOWNLOAD_FAILED

        if isinstance(exception, DownloadError):
            # Analyze download error message
            if "http error 404" in error_str or "not found" in error_str:
                return ErrorCategory.VIDEO_UNAVAILABLE
            elif "http error 403" in error_str or "forbidden" in error_str:
                # Check for geo-blocking indicators
                if (
                    "geo" in error_str
                    or "region" in error_str
                    or "location" in error_str
                ):
                    return ErrorCategory.GEO_BLOCKED
                # Check for login requirements
                elif (
                    "login" in error_str
                    or "sign in" in error_str
                    or "authenticate" in error_str
                ):
                    return ErrorCategory.LOGIN_REQUIRED
                else:
                    return ErrorCategory.VIDEO_UNAVAILABLE
            elif "http error 429" in error_str or "too many requests" in error_str:
                return ErrorCategory.PLATFORM_RATE_LIMITED
            elif "format" in error_str and (
                "not available" in error_str or "not found" in error_str
            ):
                return ErrorCategory.FORMAT_NOT_SUPPORTED
            elif (
                "network" in error_str
                or "connection" in error_str
                or "timeout" in error_str
            ):
                return ErrorCategory.NETWORK_ERROR
            else:
                return ErrorCategory.DOWNLOAD_FAILED

        # Check error message content for common patterns
        if "url" in error_str and (
            "invalid" in error_str or "unsupported" in error_str
        ):
            return ErrorCategory.INVALID_URL
        elif (
            "unavailable" in error_str
            or "private" in error_str
            or "deleted" in error_str
        ):
            return ErrorCategory.VIDEO_UNAVAILABLE
        elif "format" in error_str and "not" in error_str:
            return ErrorCategory.FORMAT_NOT_SUPPORTED
        elif "too large" in error_str or "file size" in error_str:
            return ErrorCategory.FILE_TOO_LARGE
        elif (
            "network" in error_str
            or "connection" in error_str
            or "timeout" in error_str
        ):
            return ErrorCategory.NETWORK_ERROR
        elif "rate limit" in error_str or "too many" in error_str:
            return ErrorCategory.PLATFORM_RATE_LIMITED
        elif "geo" in error_str or "region" in error_str or "location" in error_str:
            return ErrorCategory.GEO_BLOCKED
        elif (
            "login" in error_str
            or "sign in" in error_str
            or "authenticate" in error_str
        ):
            return ErrorCategory.LOGIN_REQUIRED
        else:
            return ErrorCategory.SYSTEM_ERROR

    def _handle_error(self, job_id: str, exception: Exception) -> DownloadResult:
        """
        Handle error, categorize, fail job, and publish JobFailedEvent.

        Args:
            job_id: Job identifier
            exception: Exception that occurred

        Returns:
            DownloadResult indicating failure
        """
        # Categorize error
        if isinstance(
            exception, (DownloadError, ExtractorError, UnavailableVideoError)
        ):
            error_category = self._categorize_download_error(exception)
            technical_message = f"yt-dlp error: {str(exception)}"
        else:
            error_category = ErrorCategory.SYSTEM_ERROR
            technical_message = (
                f"Unexpected error: {type(exception).__name__}: {str(exception)}"
            )

        # Get user-friendly error message
        from domain.errors import ERROR_MESSAGES

        error_info = ERROR_MESSAGES.get(
            error_category, ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]
        )
        user_message = f"{error_info['title']}: {error_info['message']}"

        # Log error
        logger.error(
            f"Job {job_id} failed with {error_category.value}: {technical_message}",
            exc_info=True,
        )

        # Fail job
        try:
            job = self.job_manager.fail_job(job_id, user_message, error_category.value)
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status: {e}")
            # Create a minimal job object for the result
            from domain.job_management.entities import DownloadJob

            job = DownloadJob.create(url="", format_id="")
            job.job_id = job_id

        # Publish JobFailedEvent
        event = JobFailedEvent(
            aggregate_id=job_id,
            occurred_at=datetime.utcnow(),
            error_message=user_message,
            error_category=error_category.value,
        )
        self.event_publisher.publish(event)

        return DownloadResult.create_failure(job, error_category, user_message)
