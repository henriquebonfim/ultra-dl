"""
API Models for request/response validation and Swagger documentation
"""

from flask_restx import fields

from src.api.v1 import api

# =============================================================================
# Request Models
# =============================================================================

url_request = api.model(
    "UrlRequest",
    {
        "url": fields.String(
            required=True,
            description="YouTube video URL",
            example="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
    },
)

download_request = api.model(
    "DownloadRequest",
    {
        "url": fields.String(
            required=True,
            description="YouTube video URL",
            example="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ),
        "format_id": fields.String(
            required=False,
            description="Format ID (optional, legacy)",
            example="137+140",
        ),
        "quality": fields.String(
            description="Target video quality (height)", example="1080"
        ),
        "format": fields.String(description="Target container format", example="mp4"),
        "mute_audio": fields.Boolean(
            description="Remove audio from download", default=False
        ),
        "mute_video": fields.Boolean(
            description="Remove video from download (audio only)", default=False
        ),
        "start_time": fields.Integer(
            description="Start time in seconds for trimming", required=False, min=0
        ),
        "end_time": fields.Integer(
            description="End time in seconds for trimming", required=False, min=0
        ),
    },
)

# =============================================================================
# Response Models
# =============================================================================

progress_detail = api.model(
    "ProgressDetail",
    {
        "percentage": fields.Integer(
            description="Progress percentage (0-100)", min=0, max=100
        ),
        "phase": fields.String(description="Current processing phase"),
        "speed": fields.String(description="Download speed", allow_null=True),
        "eta": fields.String(description="Estimated time remaining", allow_null=True),
    },
)

format_model = api.model(
    "Format",
    {
        "format_id": fields.String(description="Unique format identifier"),
        "ext": fields.String(description="File extension"),
        "resolution": fields.String(
            description="Resolution string (e.g., '1920x1080')"
        ),
        "height": fields.Integer(description="Video height in pixels"),
        "note": fields.String(description="Format notes/quality"),
        "filesize": fields.Integer(
            description="Approximate file size in bytes", allow_null=True
        ),
        "vcodec": fields.String(description="Video codec"),
        "acodec": fields.String(description="Audio codec"),
        "quality_label": fields.String(
            description="Quality label (Ultra, Excellent, Great, Good, Standard)"
        ),
        "type": fields.String(
            description="Format type (video+audio, video_only, audio_only)"
        ),
    },
)

video_meta = api.model(
    "VideoMeta",
    {
        "id": fields.String(description="YouTube video ID"),
        "title": fields.String(description="Video title"),
        "uploader": fields.String(description="Channel name"),
        "duration": fields.Integer(description="Duration in seconds"),
        "thumbnail": fields.String(description="Thumbnail URL"),
    },
)

resolutions_response = api.model(
    "ResolutionsResponse",
    {
        "meta": fields.Nested(video_meta, description="Video metadata"),
        "formats": fields.List(
            fields.Nested(format_model), description="Available formats"
        ),
    },
)

job_response = api.model(
    "JobResponse",
    {
        "job_id": fields.String(description="Unique job identifier"),
        "status": fields.String(
            description="Job status",
            enum=["pending", "processing", "completed", "failed"],
        ),
        "message": fields.String(description="Status message"),
    },
)

job_status_response = api.model(
    "JobStatusResponse",
    {
        "job_id": fields.String(description="Job identifier"),
        "status": fields.String(
            description="Job status",
            enum=["pending", "processing", "completed", "failed"],
        ),
        "progress": fields.Nested(progress_detail, description="Progress details"),
        "download_url": fields.String(
            description="Download URL when completed", allow_null=True
        ),
        "expire_at": fields.String(
            description="When the download URL expires (ISO timestamp)", allow_null=True
        ),
        "time_remaining": fields.Integer(
            description="Seconds until file expires", allow_null=True
        ),
        "error": fields.String(description="Error message if failed", allow_null=True),
        "error_category": fields.String(
            description="Error category if failed", allow_null=True
        ),
    },
)

error_response = api.model(
    "ErrorResponse",
    {
        "error": fields.String(description="Error message"),
        "category": fields.String(description="Error category", allow_null=True),
        "details": fields.Raw(description="Additional error details", allow_null=True),
    },
)

health_response = api.model(
    "HealthResponse",
    {
        "status": fields.String(
            description="Overall health status", enum=["ok", "degraded"]
        ),
        "message": fields.String(description="Health message"),
        "redis": fields.String(description="Redis connection status"),
        "celery": fields.String(description="Celery availability status"),
        "socketio": fields.String(description="SocketIO availability status"),
    },
)
