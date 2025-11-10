"""
Download Task

Celery task for asynchronous video downloading with comprehensive error handling.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from celery_app import celery_app
from config.redis_config import get_redis_repository
from config.socketio_config import is_socketio_enabled
from domain.errors import ERROR_MESSAGES, ErrorCategory, categorize_ytdlp_error
from domain.file_storage import FileManager, SignedUrlService
from domain.file_storage.repositories import RedisFileRepository
from domain.job_management import JobManager, JobNotFoundError
from domain.job_management.repositories import RedisJobRepository
from infrastructure.gcs_repository import GCSRepository, GCSUploadError
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, UnavailableVideoError
from billiard.exceptions import SoftTimeLimitExceeded

# Import WebSocket emitters (will be None if SocketIO not available)
try:
    from websocket_events import emit_job_completed, emit_job_failed, emit_job_progress
except ImportError:
    emit_job_progress = None
    emit_job_completed = None
    emit_job_failed = None


# Configure logging
logger = logging.getLogger(__name__)


def get_user_friendly_error(
    category: ErrorCategory, technical_message: str
) -> Dict[str, str]:
    """
    Get user-friendly error message for a given category.

    Args:
        category: Error category
        technical_message: Technical error details

    Returns:
        Dictionary with title, message, and action
    """
    error_info = ERROR_MESSAGES.get(
        category, ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]
    )

    return {
        "category": category.value,
        "title": error_info["title"],
        "message": error_info["message"],
        "action": error_info["action"],
        "technical": technical_message,
    }


@celery_app.task(bind=True, name="tasks.download_video")
def download_video(self, job_id: str, url: str, format_id: str) -> Dict[str, Any]:
    """
    Asynchronous video download task with comprehensive error handling.

    Args:
        job_id: Unique job identifier
        url: YouTube URL to download
        format_id: Format ID for yt-dlp

    Returns:
        dict: Task result with status and file information
    """
    import tempfile
    import time
    from pathlib import Path

    from domain.job_management.value_objects import JobProgress

    # Initialize job manager
    redis_repo = get_redis_repository()
    job_repo = RedisJobRepository(redis_repo)
    job_manager = JobManager(job_repo)

    # Progress tracking state
    last_progress_update = time.time()
    progress_timeout = 30  # seconds without progress update
    download_started = False
    timeout_check_active = True

    def check_progress_timeout():
        """
        Monitor progress updates and provide fallback updates if stalled.

        Runs in background to detect when yt-dlp progress hooks stop firing.
        """
        nonlocal last_progress_update, timeout_check_active

        while timeout_check_active:
            time.sleep(5)  # Check every 5 seconds

            if not timeout_check_active:
                break

            time_since_update = time.time() - last_progress_update

            # If progress hasn't updated in timeout period
            if time_since_update > progress_timeout and download_started:
                logger.warning(
                    f"Job {job_id}: Progress timeout detected ({time_since_update:.0f}s since last update)"
                )

                try:
                    # Provide fallback status update
                    current_job = job_manager.get_job(job_id)
                    if current_job.status.value == "processing":
                        # Keep current percentage but update phase
                        current_percentage = current_job.progress.percentage
                        fallback_progress = JobProgress(
                            percentage=min(current_percentage + 5, 90),
                            phase="downloading (slow)",
                            speed=None,
                            eta=None,
                        )
                        job_manager.update_job_progress(job_id, fallback_progress)
                        last_progress_update = time.time()
                        logger.info(f"Job {job_id}: Applied fallback progress update")
                except Exception as e:
                    logger.error(f"Job {job_id}: Error in timeout handler: {e}")

    def progress_hook(d: Dict[str, Any]) -> None:
        """
        yt-dlp progress hook for real-time updates.

        Extracts progress information and updates job status in Redis.
        """
        nonlocal last_progress_update, download_started

        try:
            status = d.get("status")

            if status == "downloading":
                download_started = True

                # Extract progress information
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                # Calculate percentage
                if total > 0:
                    percentage = min(
                        int((downloaded / total) * 85) + 10, 95
                    )  # 10-95% range
                else:
                    percentage = 50  # Unknown progress

                # Extract speed and ETA
                speed = d.get("speed")
                speed_str = None
                if speed:
                    # Convert to human-readable format
                    if speed > 1024 * 1024:
                        speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                    elif speed > 1024:
                        speed_str = f"{speed / 1024:.1f} KB/s"
                    else:
                        speed_str = f"{speed:.0f} B/s"

                eta = d.get("eta")  # Already in seconds

                # Create progress object
                progress = JobProgress.downloading(
                    percentage=percentage, speed=speed_str, eta=eta
                )

                # Update job progress atomically
                job_manager.update_job_progress(job_id, progress)
                last_progress_update = time.time()

                # Emit WebSocket event if available
                if is_socketio_enabled() and emit_job_progress:
                    emit_job_progress(
                        job_id,
                        {
                            "percentage": percentage,
                            "phase": "downloading",
                            "speed": speed_str,
                            "eta": eta,
                        },
                    )

                logger.debug(
                    f"Job {job_id} progress: {percentage}% (speed: {speed_str}, eta: {eta}s)"
                )

            elif status == "finished":
                # Download finished, now processing
                progress = JobProgress.processing(percentage=95)
                job_manager.update_job_progress(job_id, progress)
                last_progress_update = time.time()

                # Emit WebSocket event if available
                if is_socketio_enabled() and emit_job_progress:
                    emit_job_progress(job_id, {"percentage": 95, "phase": "processing"})

                logger.info(f"Job {job_id} download finished, processing...")

        except Exception as e:
            logger.warning(f"Error in progress hook for job {job_id}: {e}")

    try:
        # Log task start
        logger.info(
            f"Starting download job {job_id} for URL: {url}, format: {format_id}"
        )

        # Update job status to processing
        try:
            job_manager.start_job(job_id)
            last_progress_update = time.time()
        except JobNotFoundError:
            logger.error(f"Job {job_id} not found when starting download task")
            return {"status": "failed", "job_id": job_id, "error": "Job not found"}

        # Start progress timeout monitoring thread
        import threading

        timeout_thread = threading.Thread(target=check_progress_timeout, daemon=True)
        timeout_thread.start()
        logger.debug(f"Job {job_id}: Started progress timeout monitor")

        # Create temporary directory for download
        temp_dir = Path(tempfile.gettempdir()) / "ultra-dl" / job_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        output_template = str(temp_dir / "%(title)s.%(ext)s")

        # Configure yt-dlp options
        ydl_opts = {
            "format": format_id,
            "outtmpl": output_template,
            "progress_hooks": [progress_hook],
            "quiet": False,
            "no_warnings": False,
            "extract_flat": False,
            # Merge formats if needed
            "merge_output_format": "mp4",
            # Prefer ffmpeg for merging
            "prefer_ffmpeg": True,
            # Add timeout for stalled downloads
            "socket_timeout": 30,
            # Retry on errors
            "retries": 3,
            "fragment_retries": 3,
        }

        # Start download with yt-dlp
        logger.info(f"Job {job_id}: Starting yt-dlp download")

        downloaded_file = None

        with YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get filename
            info = ydl.extract_info(url, download=False)

            # Update progress to show metadata extraction complete
            progress = JobProgress(percentage=10, phase="metadata extracted")
            job_manager.update_job_progress(job_id, progress)
            last_progress_update = time.time()

            # Start actual download
            logger.info(f"Job {job_id}: Downloading video...")
            ydl.download([url])

            # Find downloaded file
            expected_filename = ydl.prepare_filename(info)
            downloaded_file = Path(expected_filename)

            # Handle progress timeout for short videos
            # If download completed quickly without progress updates
            if not download_started:
                logger.info(
                    f"Job {job_id}: Short video completed without progress updates"
                )
                progress = JobProgress.processing(percentage=95)
                job_manager.update_job_progress(job_id, progress)

        # Verify file exists
        if not downloaded_file or not downloaded_file.exists():
            raise Exception(
                f"Downloaded file not found at expected location: {downloaded_file}"
            )

        logger.info(
            f"Job {job_id}: Download completed successfully, file: {downloaded_file}"
        )

        # Initialize repositories and services
        file_repo = RedisFileRepository(redis_repo)
        file_manager = FileManager(file_repo)
        signed_url_service = SignedUrlService()
        gcs_repo = GCSRepository()

        download_url = None
        download_token = None
        expire_at = None

        # Try to upload to GCS if available
        if gcs_repo.is_available():
            try:
                logger.info(f"Job {job_id}: Uploading file to GCS...")

                # Generate unique blob name
                blob_name = gcs_repo.generate_blob_name(job_id, downloaded_file.name)

                # Determine content type based on file extension
                ext = downloaded_file.suffix.lower()
                content_type_map = {
                    ".mp4": "video/mp4",
                    ".webm": "video/webm",
                    ".mkv": "video/x-matroska",
                    ".m4a": "audio/mp4",
                    ".mp3": "audio/mpeg",
                    ".opus": "audio/opus",
                }
                content_type = content_type_map.get(ext, "application/octet-stream")

                # Upload to GCS
                gcs_repo.upload_file(
                    local_path=str(downloaded_file),
                    blob_name=blob_name,
                    content_type=content_type,
                )

                # Generate GCS signed URL with expiration time
                ttl_minutes = int(os.getenv("FILE_TTL_MINUTES", 10))
                download_url = gcs_repo.generate_signed_url(
                    blob_name=blob_name,
                    ttl_minutes=ttl_minutes,
                )
                
                # Calculate expiration time for GCS signed URL
                expire_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

                logger.info(f"Job {job_id}: File uploaded to GCS successfully")
                logger.info(f"Job {job_id}: Generated GCS signed URL with {ttl_minutes}-minute expiration")

                # Delete local file after successful upload
                try:
                    downloaded_file.unlink()
                    logger.info(f"Job {job_id}: Deleted local file after GCS upload")
                except Exception as e:
                    logger.warning(f"Job {job_id}: Failed to delete local file: {e}")

            except GCSUploadError as e:
                logger.error(f"Job {job_id}: GCS upload failed: {e}")
                logger.info(f"Job {job_id}: Falling back to local file serving")
                # Fall through to local file serving
            except Exception as e:
                logger.error(f"Job {job_id}: Unexpected error during GCS upload: {e}")
                # Fall through to local file serving

        # Fallback to local file serving if GCS not available or upload failed
        if download_url is None:
            try:
                logger.info(f"Job {job_id}: Using local file serving")

                # Register the downloaded file with 10-minute expiration
                registered_file = file_manager.register_file(
                    file_path=str(downloaded_file),
                    job_id=job_id,
                    filename=downloaded_file.name,
                    ttl_minutes=int(os.getenv("FILE_TTL_MINUTES", 10)),
                )

                # Generate signed URL with token
                signed_url = signed_url_service.generate_signed_url(
                    token=registered_file.token,
                    ttl_minutes=int(os.getenv("FILE_TTL_MINUTES", 10)),
                    include_signature=True,
                    expires_at=registered_file.expires_at,
                )

                download_url = signed_url.url
                download_token = registered_file.token
                expire_at = registered_file.expires_at

                logger.info(
                    f"Job {job_id}: Generated local signed URL with token {download_token}"
                )

            except Exception as e:
                logger.error(
                    f"Job {job_id}: Failed to register file and generate signed URL: {e}"
                )
                # Last resort fallback
                download_url = f"/api/v1/downloads/{job_id}"
                download_token = None

        # Stop timeout monitoring
        timeout_check_active = False

        # Mark job as completed with download URL and token
        job_manager.complete_job(
            job_id,
            download_url=download_url,
            download_token=download_token,
            expire_at=expire_at,
        )

        # Emit WebSocket completion event if available
        if is_socketio_enabled() and emit_job_completed:
            emit_job_completed(job_id, download_url, expire_at)

        logger.info(f"Job {job_id} completed successfully")
        return {
            "status": "completed",
            "job_id": job_id,
            "file_path": str(downloaded_file),
            "download_url": download_url,
        }

    except (DownloadError, ExtractorError, UnavailableVideoError) as e:
        # Stop timeout monitoring
        timeout_check_active = False
        # Handle yt-dlp specific errors
        error_category = categorize_ytdlp_error(e)
        technical_message = f"yt-dlp error: {str(e)}"

        # Get user-friendly error message
        error_info = get_user_friendly_error(error_category, technical_message)

        # Log detailed technical error
        logger.error(
            f"Download job {job_id} failed with {error_category.value}",
            extra={
                "job_id": job_id,
                "url": url,
                "format_id": format_id,
                "error_category": error_category.value,
                "technical_error": technical_message,
                "exception_type": type(e).__name__,
            },
        )

        # Update job status to failed with user-friendly message
        try:
            user_message = f"{error_info['title']}: {error_info['message']}"
            job_manager.fail_job(job_id, user_message, error_category.value)

            # Emit WebSocket failure event if available
            if is_socketio_enabled() and emit_job_failed:
                emit_job_failed(job_id, user_message, error_category.value)

        except Exception as update_error:
            logger.error(f"Failed to update job {job_id} status: {update_error}")

        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_info,
            "error_category": error_category.value,
        }

    except SoftTimeLimitExceeded:
        # Stop timeout monitoring
        timeout_check_active = False

        # Handle Celery soft time limit exceeded (download took too long)
        error_category = ErrorCategory.DOWNLOAD_TIMEOUT
        technical_message = "Download exceeded time limit (slow connection or large file)"

        error_info = get_user_friendly_error(error_category, technical_message)

        # Log detailed technical error
        logger.warning(
            f"Download job {job_id} exceeded time limit",
            extra={
                "job_id": job_id,
                "url": url,
                "format_id": format_id,
                "error_category": error_category.value,
                "technical_error": technical_message,
            },
        )

        # Update job status to failed
        try:
            user_message = f"{error_info['title']}: {error_info['message']}"
            job_manager.fail_job(job_id, user_message, error_category.value)

            # Emit WebSocket failure event if available
            if is_socketio_enabled() and emit_job_failed:
                emit_job_failed(job_id, user_message, error_category.value)

        except Exception as update_error:
            logger.error(f"Failed to update job {job_id} status: {update_error}")

        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_info,
            "error_category": error_category.value,
        }

    except OSError as e:
        # Stop timeout monitoring
        timeout_check_active = False

        # Handle file system errors (disk full, permission denied, etc.)
        error_str = str(e).lower()

        if "no space" in error_str or "disk full" in error_str:
            error_category = ErrorCategory.SYSTEM_ERROR
            technical_message = f"Disk space error: {str(e)}"
        elif "permission" in error_str:
            error_category = ErrorCategory.SYSTEM_ERROR
            technical_message = f"Permission error: {str(e)}"
        else:
            error_category = ErrorCategory.SYSTEM_ERROR
            technical_message = f"File system error: {str(e)}"

        error_info = get_user_friendly_error(error_category, technical_message)

        # Log detailed technical error
        logger.error(
            f"Download job {job_id} failed with file system error",
            extra={
                "job_id": job_id,
                "url": url,
                "format_id": format_id,
                "error_category": error_category.value,
                "technical_error": technical_message,
                "exception_type": type(e).__name__,
            },
        )

        # Update job status to failed
        try:
            user_message = f"{error_info['title']}: {error_info['message']}"
            job_manager.fail_job(job_id, user_message, error_category.value)

            # Emit WebSocket failure event if available
            if is_socketio_enabled() and emit_job_failed:
                emit_job_failed(job_id, user_message, error_category.value)

        except Exception as update_error:
            logger.error(f"Failed to update job {job_id} status: {update_error}")

        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_info,
            "error_category": error_category.value,
        }

    except Exception as e:
        # Stop timeout monitoring
        timeout_check_active = False

        # Handle unexpected errors
        error_category = ErrorCategory.SYSTEM_ERROR
        technical_message = f"Unexpected error: {type(e).__name__}: {str(e)}"

        error_info = get_user_friendly_error(error_category, technical_message)

        # Log detailed technical error with full context
        logger.exception(
            f"Download job {job_id} failed with unexpected error",
            extra={
                "job_id": job_id,
                "url": url,
                "format_id": format_id,
                "error_category": error_category.value,
                "technical_error": technical_message,
                "exception_type": type(e).__name__,
            },
        )

        # Update job status to failed
        try:
            user_message = f"{error_info['title']}: {error_info['message']}"
            job_manager.fail_job(job_id, user_message, error_category.value)

            # Emit WebSocket failure event if available
            if is_socketio_enabled() and emit_job_failed:
                emit_job_failed(job_id, user_message, error_category.value)

        except Exception as update_error:
            logger.error(f"Failed to update job {job_id} status: {update_error}")

        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_info,
            "error_category": error_category.value,
        }
