"""
API Namespaces - Organized endpoint groups
"""

# Import existing services
from application.video_service import VideoService
from config.gcs_config import gcs_health_check, is_gcs_enabled
from config.redis_config import redis_health_check
from config.socketio_config import is_socketio_enabled
from domain.errors import ApplicationError, ErrorCategory, categorize_ytdlp_error, create_error_response
from domain.job_management import JobNotFoundError
from domain.video_processing import InvalidUrlError, VideoProcessingError
from flask import current_app, request
from flask_restx import Namespace, Resource

from api.v1.models import (
    download_request,
    error_response,
    health_response,
    job_response,
    job_status_response,
    resolutions_response,
    url_request,
)

# =============================================================================
# Video Namespace - Video information and format retrieval
# =============================================================================

video_ns = Namespace("videos", description="Video information operations")


@video_ns.route("/resolutions")
class VideoResolutions(Resource):
    """Get available video resolutions/formats"""

    @video_ns.doc("get_video_resolutions")
    @video_ns.expect(url_request, validate=True)
    @video_ns.response(200, "Success", resolutions_response)
    @video_ns.response(400, "Bad Request", error_response)
    @video_ns.response(429, "Too Many Requests", error_response)
    def post(self):
        """
        Get available video formats and resolutions

        Extracts metadata and available formats for a YouTube video without downloading.
        Rate limit: 20 requests per minute per IP.
        """
        data = request.get_json()
        url = data.get("url", "").strip()

        if not url:
            return create_error_response(
                ErrorCategory.INVALID_REQUEST,
                "Empty URL provided",
                status_code=400
            )

        try:
            # Use VideoService from application layer
            video_service = VideoService()
            result = video_service.get_video_info(url)
            
            return result, 200

        except InvalidUrlError as e:
            return create_error_response(
                ErrorCategory.INVALID_URL,
                str(e),
                status_code=400
            )
        except VideoProcessingError as e:
            # Categorize the underlying yt-dlp error
            category = categorize_ytdlp_error(e)
            return create_error_response(
                category,
                str(e),
                status_code=400
            )
        except Exception as e:
            current_app.logger.exception(f"Unexpected error in /resolutions: {str(e)}")
            return create_error_response(
                ErrorCategory.SYSTEM_ERROR,
                f"Unexpected error: {str(e)}",
                status_code=500
            )


# =============================================================================
# Job Namespace - Job management operations
# =============================================================================

job_ns = Namespace("jobs", description="Job management operations")


@job_ns.route("/<string:job_id>")
@job_ns.param("job_id", "The job identifier")
class Job(Resource):
    """Job status operations"""

    @job_ns.doc("get_job_status")
    @job_ns.marshal_with(job_status_response, code=200)
    @job_ns.response(404, "Job Not Found", error_response)
    @job_ns.response(500, "Internal Server Error", error_response)
    def get(self, job_id):
        """
        Get job status and progress

        Poll this endpoint to track download progress. Returns job status,
        progress percentage, and download URL when completed.
        """
        try:
            # Get job_service from app context
            job_service = current_app.job_service
            if not job_service:
                return create_error_response(
                    ErrorCategory.SYSTEM_ERROR,
                    "Job service not initialized",
                    status_code=503
                )
            
            job_data = job_service.get_job_status(job_id)

            if not job_data:
                return create_error_response(
                    ErrorCategory.JOB_NOT_FOUND,
                    f"Job {job_id} not found",
                    status_code=404
                )

            return job_data, 200

        except JobNotFoundError:
            return create_error_response(
                ErrorCategory.JOB_NOT_FOUND,
                f"Job {job_id} not found",
                status_code=404
            )
        except ApplicationError as e:
            return create_error_response(
                e.category,
                str(e),
                status_code=400
            )
        except Exception as e:
            current_app.logger.exception(f"Error getting job status for {job_id}: {str(e)}")
            return create_error_response(
                ErrorCategory.SYSTEM_ERROR,
                f"Internal server error: {str(e)}",
                status_code=500
            )

    @job_ns.doc("delete_job")
    @job_ns.response(204, "Job deleted/cancelled successfully")
    @job_ns.response(404, "Job Not Found", error_response)
    @job_ns.response(500, "Internal Server Error", error_response)
    def delete(self, job_id):
        """
        Delete or cancel a job

        - For pending/processing jobs: Cancels the job and cleans up resources
        - For completed/failed jobs: Deletes the job record and associated file
        
        This endpoint can be used to cancel active downloads or clean up completed ones.
        """
        try:
            # Get job_service from app context
            job_service = current_app.job_service
            if not job_service:
                return create_error_response(
                    ErrorCategory.SYSTEM_ERROR,
                    "Job service not initialized",
                    status_code=503
                )

            # Check if job exists
            try:
                job_data = job_service.get_job_status(job_id)
            except JobNotFoundError:
                return create_error_response(
                    ErrorCategory.JOB_NOT_FOUND,
                    f"Job {job_id} not found",
                    status_code=404
                )
            
            if not job_data:
                return create_error_response(
                    ErrorCategory.JOB_NOT_FOUND,
                    f"Job {job_id} not found",
                    status_code=404
                )

            # If job is pending or processing, try to revoke the Celery task
            job_status = job_data.get("status")
            if job_status in ["pending", "processing"]:
                try:
                    from celery_app import celery_app
                    # Revoke the task (terminate if already started)
                    celery_app.control.revoke(job_id, terminate=True, signal='SIGKILL')
                    current_app.logger.info(f"Revoked Celery task for job {job_id}")
                except Exception as e:
                    current_app.logger.warning(f"Failed to revoke Celery task for job {job_id}: {str(e)}")

            # Delete the job and file
            success = job_service.delete_job(job_id)
            if success:
                return "", 204
            else:
                return create_error_response(
                    ErrorCategory.SYSTEM_ERROR,
                    "Failed to delete job",
                    status_code=500
                )

        except ApplicationError as e:
            return create_error_response(
                e.category,
                str(e),
                status_code=400
            )
        except Exception as e:
            current_app.logger.exception(f"Error deleting job {job_id}: {str(e)}")
            return create_error_response(
                ErrorCategory.SYSTEM_ERROR,
                f"Internal server error: {str(e)}",
                status_code=500
            )


# =============================================================================
# Download Namespace - Download operations
# =============================================================================

download_ns = Namespace("downloads", description="Download operations")


@download_ns.route("/")
class Download(Resource):
    """Initiate video download"""

    @download_ns.doc("create_download")
    @download_ns.expect(download_request, validate=True)
    @download_ns.marshal_with(job_response, code=202)
    @download_ns.response(400, "Bad Request", error_response)
    @download_ns.response(429, "Too Many Requests", error_response)
    @download_ns.response(503, "Service Unavailable", error_response)
    def post(self):
        """
        Start a video download job

        Creates an asynchronous job to download the video in the specified format.
        Returns a job_id that can be used to track progress.
        Rate limit: 10 requests per minute per IP.
        """
        data = request.get_json()
        url = data.get("url", "").strip()
        format_id = data.get("format_id", "").strip()

        if not url:
            return create_error_response(
                ErrorCategory.INVALID_REQUEST,
                "Missing 'url' in request body",
                status_code=400
            )
        if not format_id:
            return create_error_response(
                ErrorCategory.INVALID_REQUEST,
                "Missing 'format_id' in request body",
                status_code=400
            )

        try:
            # Validate URL format
            video_service = VideoService()
            if not video_service.validate_url(url):
                return create_error_response(
                    ErrorCategory.INVALID_URL,
                    "Invalid YouTube URL format",
                    status_code=400
                )
            
            # Get job_service from app context
            job_service = current_app.job_service
            job_data = job_service.create_download_job(url, format_id)
            job_id = job_data["job_id"]

            # Enqueue Celery task for background processing
            celery = current_app.celery
            if celery is not None:
                try:
                    celery.send_task(
                        "tasks.download_video", args=(job_id, url, format_id)
                    )
                    current_app.logger.info(
                        f"[API_V1] Enqueued Celery task for job {job_id}"
                    )
                except Exception as e:
                    current_app.logger.exception(
                        f"Failed to enqueue Celery task for job {job_id}: {e}"
                    )
                    return create_error_response(
                        ErrorCategory.SYSTEM_ERROR,
                        "Failed to enqueue background task",
                        status_code=500
                    )
            else:
                current_app.logger.warning(
                    f"[API_V1] Celery not available, job {job_id} will not be processed"
                )
                return create_error_response(
                    ErrorCategory.SYSTEM_ERROR,
                    "Background task system not available",
                    status_code=503
                )

            return job_data, 202

        except ApplicationError as e:
            return create_error_response(
                e.category,
                str(e),
                status_code=400
            )
        except Exception as e:
            current_app.logger.exception(f"Unexpected error creating download job: {str(e)}")
            return create_error_response(
                ErrorCategory.SYSTEM_ERROR,
                f"Failed to create download job: {str(e)}",
                status_code=500
            )


@download_ns.route("/file/<string:token>")
@download_ns.param("token", "The download token")
class DownloadFile(Resource):
    """Download file by token"""

    @download_ns.doc("download_file")
    @download_ns.response(200, "File content")
    @download_ns.response(400, "Bad Request", error_response)
    @download_ns.response(403, "Forbidden", error_response)
    @download_ns.response(404, "File Not Found", error_response)
    @download_ns.response(410, "File Expired", error_response)
    @download_ns.response(503, "Service Unavailable", error_response)
    def get(self, token):
        """
        Download file using secure token

        Uses the download token from a completed job to download the actual video file.
        Tokens expire after a configured time period (default: 10 minutes).
        """
        # Check if file manager is available
        if not hasattr(current_app, "file_manager") or current_app.file_manager is None:
            return create_error_response(
                ErrorCategory.SYSTEM_ERROR,
                "File service not initialized",
                status_code=503
            )

        # Validate token format
        if not token or not token.strip():
            return create_error_response(
                ErrorCategory.INVALID_REQUEST,
                "Invalid or missing token",
                status_code=400
            )

        # Get optional signature from query parameters
        signature = request.args.get("signature")

        try:
            # Retrieve file by token
            current_app.logger.debug(
                f"[DOWNLOAD_FILE_V1] Retrieving file for token {token[:8]}..."
            )

            file = current_app.file_manager.get_file_by_token(token)

            # Validate signature if provided
            if signature and hasattr(current_app, "signed_url_service"):
                if not current_app.signed_url_service.validate_signature(
                    token, signature, file.expires_at
                ):
                    current_app.logger.warning(
                        f"[DOWNLOAD_FILE_V1] Invalid signature for token {token[:8]}"
                    )
                    return create_error_response(
                        ErrorCategory.INVALID_REQUEST,
                        "Invalid signature",
                        status_code=403
                    )

            # Check if physical file exists
            if not file.file_exists():
                current_app.logger.error(
                    f"[DOWNLOAD_FILE_V1] Physical file not found: {file.file_path}"
                )
                return create_error_response(
                    ErrorCategory.FILE_NOT_FOUND,
                    "File not found on server",
                    status_code=404
                )

            # Log successful access
            current_app.logger.info(
                f"[DOWNLOAD_FILE_V1] Serving file {file.filename} for token {token[:8]}"
            )

            # Serve the file
            from flask import send_file

            return send_file(
                file.file_path,
                as_attachment=True,
                download_name=file.filename,
                mimetype="application/octet-stream",
            )

        except Exception as e:
            error_str = str(e).lower()

            # Handle specific exceptions
            if "not found" in error_str:
                current_app.logger.warning(
                    f"[DOWNLOAD_FILE_V1] File not found for token {token[:8]}"
                )
                return create_error_response(
                    ErrorCategory.FILE_NOT_FOUND,
                    "File not found or token invalid",
                    status_code=404
                )
            elif "expired" in error_str:
                current_app.logger.warning(
                    f"[DOWNLOAD_FILE_V1] File expired for token {token[:8]}"
                )
                return create_error_response(
                    ErrorCategory.FILE_EXPIRED,
                    "File has expired. Please download the video again.",
                    status_code=410
                )
            else:
                current_app.logger.exception(
                    f"[DOWNLOAD_FILE_V1] Error serving file for token {token[:8]}: {str(e)}"
                )
                return create_error_response(
                    ErrorCategory.SYSTEM_ERROR,
                    f"Internal server error: {str(e)}",
                    status_code=500
                )


# =============================================================================
# System Namespace - System health and monitoring
# =============================================================================

system_ns = Namespace("system", description="System health and monitoring operations")


@system_ns.route("/health")
class Health(Resource):
    """System health check"""

    @system_ns.doc("health_check")
    @system_ns.marshal_with(health_response, code=200)
    @system_ns.response(503, "Service Degraded", health_response)
    def get(self):
        """
        Check system health and service availability

        Returns the health status of all system components including Redis,
        Celery, GCS, and SocketIO. This endpoint is exempt from rate limiting.
        """
        health_status = {
            "status": "ok",
            "message": "backend ready",
            "redis": "unknown",
            "celery": "unknown",
            "gcs": "unknown",
            "socketio": "unknown",
        }

        # Check Redis connectivity
        try:
            if redis_health_check():
                health_status["redis"] = "connected"
            else:
                health_status["redis"] = "disconnected"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["redis"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        # Check Celery availability
        if current_app.celery is not None:
            health_status["celery"] = "available"
        else:
            health_status["celery"] = "unavailable"
            health_status["status"] = "degraded"

        # Check GCS availability (optional - not critical)
        try:
            if is_gcs_enabled():
                if gcs_health_check():
                    health_status["gcs"] = "connected"
                else:
                    health_status["gcs"] = "disconnected"
            else:
                health_status["gcs"] = "not_configured"
        except Exception as e:
            health_status["gcs"] = f"error: {str(e)}"

        # Check SocketIO availability (optional - not critical)
        if is_socketio_enabled():
            health_status["socketio"] = "available"
        else:
            health_status["socketio"] = "not_configured"

        status_code = 200 if health_status["status"] == "ok" else 503
        return health_status, status_code
