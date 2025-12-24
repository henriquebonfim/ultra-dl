"""
Download Service

Application service that orchestrates the complete video download workflow.
Coordinates domain services and publishes domain events for state transitions.
"""

import logging
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, UnavailableVideoError

from src.domain.errors import ErrorCategory
from src.domain.file_storage.services import FileManager
from src.domain.file_storage.storage_repository import IFileStorageRepository
from src.domain.job_management.services import JobManager
from src.domain.job_management.value_objects import JobProgress
from src.domain.video_processing.services import VideoProcessor
from src.infrastructure.event_handlers import (
    emit_websocket_job_completed,
    emit_websocket_job_failed,
    emit_websocket_job_progress,
    emit_websocket_job_warning,
)

from .download_result import DownloadResult

logger = logging.getLogger(__name__)


class DownloadService:
    """
    Application service for orchestrating the full video download workflow.

    Coordinates multiple domain services (JobManager, FileManager, VideoProcessor)
    and infrastructure repositories (IFileStorageRepository) to execute the complete
    end-to-end download process. This service is used by:
    - Celery background tasks (asynchronous download processing)

    DownloadService orchestrates the entire workflow from start to finish and does NOT
    handle individual job CRUD operations. For job lifecycle management, see JobService.

    Workflow orchestration:
    1. Start job and update status
    2. Download video using yt-dlp with progress tracking
    3. Store file to local storage
    4. Generate download URL
    5. Complete job with download information
    6. Handle errors with categorization and user-friendly messages
    7. Emit WebSocket events at each state transition

    Responsibilities:
    - Execute complete download workflow
    - Coordinate domain services and infrastructure
    - Track download progress with real-time updates
    - Categorize and handle download errors
    - Emit WebSocket events for client notifications
    - Manage temporary files and cleanup

    Note: Both JobService and DownloadService serve legitimate separate purposes:
    - JobService: Job lifecycle CRUD (used by API/WebSocket layers)
    - DownloadService: Full download workflow orchestration (used by Celery tasks)
    """

    def __init__(
        self,
        job_manager: JobManager,
        file_manager: FileManager,
        video_processor: VideoProcessor,
        storage_repository: IFileStorageRepository,
    ):
        """
        Initialize Download Service with dependencies.

        Args:
            job_manager: Domain service for job lifecycle management
            file_manager: Domain service for file storage management
            video_processor: Domain service for video processing
            storage_repository: Infrastructure repository for file storage (IFileStorageRepository)
        """
        self.job_manager = job_manager
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.storage_repository = storage_repository

    def execute_download(
        self,
        job_id: str,
        url: str,
        format_id: str,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        quality: Optional[str] = None,
        format_str: Optional[str] = None,
        mute_audio: bool = False,
        mute_video: bool = False,
    ) -> DownloadResult:
        """
        Execute complete video download workflow.

        Workflow:
        1. Start job and publish JobStartedEvent
        2. Download video with yt-dlp and progress callbacks
        3. Store file locally
        4. Generate download URL
        5. Complete job and publish JobCompletedEvent
        6. On error: categorize, fail job, publish JobFailedEvent

        Args:
            job_id: Unique job identifier
            url: YouTube URL to download
            format_id: Format ID for yt-dlp (legacy/direct)
            progress_callback: Optional callback for progress updates
            start_time: Start trimming time
            end_time: End trimming time
            quality: Video quality/height (e.g. "1080")
            format_str: Container format (e.g. "mp4")
            mute_audio: Remove audio
            mute_video: Remove video

        Returns:
            DownloadResult with success/failure information
        """
        try:
            # Start job and publish event
            job = self._start_job(job_id, url, format_id or "auto")

            # Download video with progress tracking
            downloaded_file = self._download_video(
                job_id,
                url,
                format_id,
                progress_callback,
                start_time,
                end_time,
                quality,
                format_str,
                mute_audio,
                mute_video,
            )

            # Store file and generate download URL
            download_url, expire_at = self._store_file(job_id, downloaded_file)

            # Complete job and publish event
            job = self._complete_job(job_id, download_url, expire_at)

            logger.info(f"Job {job_id} completed successfully")
            return DownloadResult(
                success=True,
                file_path=str(downloaded_file) if downloaded_file else None,
                error_message=None,
                error_type=None,
            )

        except Exception as e:
            # Handle error, categorize, and publish failure event
            return self._handle_error(job_id, e)

    def _start_job(self, job_id: str, url: str, format_id: str) -> Any:
        """
        Start job.

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

        return job

    def _download_video(
        self,
        job_id: str,
        url: str,
        format_id: str,
        progress_callback: Optional[Callable[[JobProgress], None]],
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        quality: Optional[str] = None,
        format_str: Optional[str] = None,
        mute_audio: bool = False,
        mute_video: bool = False,
    ) -> Path:
        """
        Download video with yt-dlp and progress callbacks.
        """

        # Create a custom logger to intercept yt-dlp warnings
        class YtDlpLogger:
            def debug(self, msg):
                for line in msg.splitlines():
                    if line.strip():
                        pass

            def info(self, msg):
                pass

            def warning(self, msg):
                if not msg:
                    return

                # Check for network-related retries/warnings
                if any(
                    x in msg
                    for x in [
                        "Connection refused",
                        "Retrying",
                        "Network is unreachable",
                        "111",
                    ]
                ):
                    logger.warning(f"Job {job_id} network warning: {msg}")
                    emit_websocket_job_warning(job_id, msg)
                else:
                    logger.warning(f"yt-dlp warning: {msg}")

            def error(self, msg):
                logger.error(f"yt-dlp error: {msg}")

        logger.info(f"Job {job_id}: Starting video download")

        # Construct format string
        final_format = format_id

        if not final_format:
            if mute_video:
                final_format = "bestaudio/best"
            else:
                # Video required
                video_selector = (
                    f"bestvideo[height<={quality}]" if quality else "bestvideo"
                )
                audio_selector = "bestaudio" if not mute_audio else None

                if audio_selector:
                    final_format = (
                        f"{video_selector}+{audio_selector}/best[height<={quality}]"
                        if quality
                        else f"{video_selector}+{audio_selector}/best"
                    )
                else:
                    final_format = video_selector

        logger.info(f"Job {job_id}: Using format selector: {final_format}")

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

                    # Emit WebSocket progress event
                    emit_websocket_job_progress(job_id, progress)

                    # Call external progress callback if provided
                    if progress_callback:
                        progress_callback(progress)

                elif status == "finished":
                    # Download finished, now processing
                    progress = JobProgress.processing(percentage=95)
                    self.job_manager.update_job_progress(job_id, progress)

                    # Emit WebSocket progress event
                    emit_websocket_job_progress(job_id, progress)

                    # Call external progress callback if provided
                    if progress_callback:
                        progress_callback(progress)

            except Exception as e:
                logger.warning(f"Error in progress hook for job {job_id}: {e}")

        # Create post-processor hook for granular status updates
        def post_processor_hook(d: Dict[str, Any]) -> None:
            """yt-dlp post-processor hook for status updates during conversion/trimming."""
            try:
                status = d.get("status")
                postprocessor = d.get("postprocessor")

                if status == "started":
                    progress = None
                    if postprocessor == "FFmpegVideoConvertor":
                        progress = JobProgress.converting(percentage=96)
                    elif postprocessor == "FFmpegMerger":
                        progress = JobProgress.merging(percentage=95)
                    elif postprocessor == "FixupM3u8" or postprocessor == "FixupM4a":
                        progress = JobProgress.processing(percentage=95)
                    else:
                        # Generic processing for other PPs
                        progress = JobProgress.processing(percentage=95)

                    if progress:
                        self.job_manager.update_job_progress(job_id, progress)
                        emit_websocket_job_progress(job_id, progress)

                elif status == "finished":
                    # If we just finished a major step, we might bump percentage slightly
                    pass

            except Exception as e:
                logger.warning(f"Error in post-processor hook for job {job_id}: {e}")

        # Configure yt-dlp options with performance optimizations
        ydl_opts = {
            "format": final_format,
            "outtmpl": output_template,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [post_processor_hook],
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": (
                        format_str if mute_video and format_str else "mp4"
                    ),
                }
            ],
            "quiet": False,
            "no_warnings": False,
            # Performance optimizations
            "merge_output_format": (
                format_str if mute_video and format_str else "mp4"
            ),  # Efficient container format
            "prefer_ffmpeg": True,  # Use ffmpeg for faster processing
            # Network optimizations
            "socket_timeout": 30,  # 30s timeout for network operations
            "logger": YtDlpLogger(),
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

        if start_time is not None and end_time is not None:
            logger.info(
                f"Job {job_id}: Configuring trim from {start_time} to {end_time}"
            )
            ydl_opts["download_sections"] = f"*{start_time}-{end_time}"

            # Force keyframes for precision
            ydl_opts["force_keyframes_at_cuts"] = True

            # Default container for trimmed output should be webm unless explicitly provided
            target_format = format_str if format_str else "webm"

            # Append, don't overwrite
            if "postprocessors" not in ydl_opts:
                ydl_opts["postprocessors"] = []

            # Check if we already have a convertor
            has_convertor = any(
                p.get("key") == "FFmpegVideoConvertor"
                for p in ydl_opts["postprocessors"]
            )

            if not has_convertor:
                ydl_opts["postprocessors"].append(
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": target_format,
                    }
                )
            else:
                # Update existing convertor to use target_format when trimming is configured
                for p in ydl_opts["postprocessors"]:
                    if p.get("key") == "FFmpegVideoConvertor":
                        p["preferedformat"] = target_format

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

        # Generate download URL for local storage
        ttl_minutes = 10
        expire_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

        # Register file and generate download URL
        full_file_path = str(self.storage_repository.base_path / storage_path)
        registered_file = self.file_manager.register_file(
            file_path=full_file_path,
            job_id=job_id,
            filename=downloaded_file.name,
            ttl_minutes=ttl_minutes,
        )

        download_url = registered_file.generate_download_url(
            base_url="/api/v1/downloads/file"
        )
        expire_at = registered_file.expires_at
        logger.info(f"Job {job_id}: Generated local download URL")

        return download_url, expire_at

    def _complete_job(self, job_id: str, download_url: str, expire_at: datetime) -> Any:
        """
        Complete job and emit WebSocket completion event.

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

        # Emit WebSocket completion event
        emit_websocket_job_completed(job_id, download_url, expire_at)

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
        elif "age-restricted" in error_str or "confirm your age" in error_str:
            return ErrorCategory.AGE_RESTRICTED
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
        Handle error, categorize, fail job, and emit WebSocket failure event.

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
        from src.domain.errors import ERROR_MESSAGES

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
            from src.domain.job_management.entities import DownloadJob

            job = DownloadJob.create(url="", format_id="")
            job.job_id = job_id

        # Emit WebSocket failure event
        emit_websocket_job_failed(job_id, user_message, error_category.value)

        return DownloadResult(
            success=False,
            file_path=None,
            error_message=user_message,
            error_type=error_category.value,
        )
