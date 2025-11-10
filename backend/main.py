"""
main.py

Flask backend with Celery integration for asynchronous YouTube downloading.
This version integrates Redis for job persistence and Celery for background processing.

Dependencies:
  - Python packages: Flask, yt-dlp, flask-cors, redis, celery
  - System: ffmpeg (must be on PATH for merging/processing)
  - Infrastructure: Redis server

Notes:
  - Uses Redis for job persistence and Celery for async processing
  - API v1 endpoints available at /api/v1/ with Swagger docs at /api/v1/docs
"""

import os

from application.job_service import JobService
from config.celery_config import make_celery
from config.gcs_config import gcs_health_check, init_gcs, is_gcs_enabled

# Import Celery, Redis, GCS, and SocketIO configuration
from config.redis_config import get_redis_repository, init_redis, redis_health_check
from config.socketio_config import init_socketio, is_socketio_enabled

# Import domain services and errors
from domain.errors import (
    ErrorCategory,
    create_error_response,
)
from domain.file_storage import FileManager, SignedUrlService
from domain.file_storage.repositories import RedisFileRepository
from domain.job_management import JobManager
from domain.job_management.repositories import RedisJobRepository
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import WebSocket event handlers
from websocket_events import register_socketio_events

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
        "expose_headers": ["Content-Type", "X-Total-Count"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Get API version from environment
API_VERSION = os.getenv("API_VERSION", "v1")

# Check if we're in production mode
FLASK_ENV = os.getenv("FLASK_ENV", "development")
IS_PRODUCTION = FLASK_ENV == "production"

# Initialize rate limiter with Redis storage (only in production)
if IS_PRODUCTION:
    daily_limit = os.getenv("RATE_LIMIT_DAILY", "200")
    hourly_limit = os.getenv("RATE_LIMIT_HOURLY", "50")
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{daily_limit} per day", f"{hourly_limit} per hour"],
        storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        strategy="fixed-window",
    )
    print(f"Rate limiting ENABLED (production mode) - {daily_limit}/day, {hourly_limit}/hour")
else:
    # Disable rate limiting in development
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[],  # No default limits
        enabled=False,  # Disable rate limiting
    )
    print("Rate limiting DISABLED (development mode)")

# Store limiter in app for access in blueprints
app.limiter = limiter


# Custom error handler for rate limit exceeded (only relevant in production)
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors."""
    return create_error_response(
        ErrorCategory.RATE_LIMITED,
        f"Rate limit exceeded: {e.description}",
        status_code=429,
    )


# Initialize Redis, Celery, GCS, and SocketIO
try:
    init_redis()
    celery = make_celery(app)
    app.celery = celery
    print("Redis and Celery initialized successfully")

    # Initialize GCS (optional - system works without it)
    gcs_initialized = init_gcs()
    if gcs_initialized:
        print("GCS initialized successfully")
    else:
        print("GCS not configured - using local file serving")

    # Initialize SocketIO (optional - system falls back to polling)
    try:
        # Only initialize SocketIO if we plan to use it
        socketio_enabled = os.getenv("SOCKETIO_ENABLED", "true").lower() == "true"
        if socketio_enabled:
            socketio = init_socketio(app)
            app.socketio = socketio
            # Register WebSocket event handlers
            register_socketio_events(app)
            print("SocketIO initialized successfully")
        else:
            socketio = None
            print("SocketIO disabled - using polling fallback")
    except Exception as e:
        print(f"Warning: Could not initialize SocketIO: {e}")
        print("WebSocket support disabled - using polling fallback")
        socketio = None

    # Initialize repositories
    redis_repo = get_redis_repository()

    # Initialize file manager and signed URL service
    file_repository = RedisFileRepository(redis_repo)
    file_manager = FileManager(file_repository)
    signed_url_service = SignedUrlService()

    # Initialize job service
    job_repository = RedisJobRepository(redis_repo)
    job_manager = JobManager(job_repository)
    job_service = JobService(job_manager, file_manager)
    app.job_service = job_service
    app.file_manager = file_manager
    app.signed_url_service = signed_url_service

    # Register API v1 blueprint with Swagger documentation
    from api.v1 import api_v1_bp

    app.register_blueprint(api_v1_bp)
    
    # Apply specific rate limits to API endpoints (only in production)
    if IS_PRODUCTION:
        try:
            limiter.limit("20 per minute")(app.view_functions[f"api_{API_VERSION}.videos_video_resolutions"])
            limiter.limit("10 per minute")(app.view_functions[f"api_{API_VERSION}.downloads_download"])
            limiter.limit("30 per minute")(app.view_functions[f"api_{API_VERSION}.jobs_job"])  # Job status polling
            print("Specific rate limits applied to API endpoints")
        except KeyError as e:
            print(f"Warning: Could not apply rate limits to some endpoints: {e}")
    else:
        print("Skipping rate limit configuration (development mode)")
    
    print(
        f"API {API_VERSION} registered at /api/{API_VERSION} with Swagger UI at /api/{API_VERSION}/docs"
    )

except Exception as e:
    print(f"Warning: Could not initialize Redis/Celery: {e}")
    celery = None
    job_service = None
    socketio = None


@app.route("/health", methods=["GET"])
@limiter.exempt  # Exempt health check from rate limiting
def health():
    """
    Legacy health check endpoint for backward compatibility.
    
    Note: The documented health endpoint is available at /api/v1/system/health
    in the Swagger documentation. This endpoint is kept for backward compatibility
    and simple health checks without API versioning.
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
    if celery is not None:
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
    return jsonify(health_status), status_code


if __name__ == "__main__":
    # Run on port 8000 (Replit allowed port) to avoid conflict with Vite frontend on 5000
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # Use SocketIO.run if available, otherwise fall back to app.run
    if is_socketio_enabled():
        from config.socketio_config import get_socketio

        socketio = get_socketio()
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=debug)
