"""
Application Factory

Creates and configures Flask application with all dependencies.
This factory pattern improves testability by allowing dependency injection
and configuration overrides.
"""

import os
from typing import Optional

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from application.dependency_container import DependencyContainer
from application.download_service import DownloadService
from application.event_publisher import EventPublisher
from application.job_service import JobService
from application.rate_limit_service import RateLimitService
from application.video_service import VideoService
from config.celery_config import make_celery
from config.gcs_config import gcs_health_check, init_gcs, is_gcs_enabled
from config.redis_config import get_redis_client, get_redis_repository, init_redis, redis_health_check
from config.socketio_config import init_socketio, is_socketio_enabled
from domain.errors import ErrorCategory, RateLimitExceededError, create_error_response
from domain.events import (
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent,
    JobStartedEvent,
)
from domain.file_storage import FileManager, SignedUrlService
from domain.job_management import JobManager
from domain.rate_limiting.services import RateLimitManager
from domain.video_processing.services import VideoProcessor
from infrastructure.event_handlers import WebSocketEventHandler
from infrastructure.local_file_storage_repository import LocalFileStorageRepository
from infrastructure.video_metadata_extractor import VideoMetadataExtractor
from infrastructure.rate_limit_config import RateLimitConfig
from infrastructure.redis_file_repository import RedisFileRepository
from infrastructure.redis_job_repository import RedisJobRepository
from infrastructure.redis_rate_limit_repository import RedisRateLimitRepository
from api.websocket_events import register_socketio_events


class AppConfig:
    """Application configuration."""
    
    def __init__(self):
        self.api_version = os.getenv("API_VERSION", "v1")
        self.flask_env = os.getenv("FLASK_ENV", "development")
        self.is_production = self.flask_env == "production"
        
        # Rate limiting configuration
        self.rate_limit_daily = os.getenv("RATE_LIMIT_DAILY", "200")
        self.rate_limit_hourly = os.getenv("RATE_LIMIT_HOURLY", "50")
        
        # SocketIO configuration
        self.socketio_enabled = os.getenv("SOCKETIO_ENABLED", "true").lower() == "true"


def create_app(config: Optional[AppConfig] = None) -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config: Application configuration, uses default if None
        
    Returns:
        Configured Flask application
    """
    if config is None:
        config = AppConfig()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configure CORS
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
    
    # Initialize rate limiter
    limiter = _create_rate_limiter(app, config)
    app.limiter = limiter
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Initialize infrastructure
    _initialize_infrastructure(app, config)
    
    # Initialize services
    _initialize_services(app)
    
    # Register blueprints
    _register_blueprints(app, config)
    
    # Register health check endpoint
    _register_health_endpoint(app, limiter)
    
    return app


def _create_rate_limiter(app: Flask, config: AppConfig) -> Limiter:
    """
    Create and configure rate limiter.
    
    Args:
        app: Flask application
        config: Application configuration
        
    Returns:
        Configured Limiter instance
    """
    if config.is_production:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[
                f"{config.rate_limit_daily} per day",
                f"{config.rate_limit_hourly} per hour"
            ],
            storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            strategy="fixed-window",
        )
        print(f"Rate limiting ENABLED (production mode) - "
              f"{config.rate_limit_daily}/day, {config.rate_limit_hourly}/hour")
    else:
        # Disable rate limiting in development
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[],
            enabled=False,
        )
        print("Rate limiting DISABLED (development mode)")
    
    return limiter


def _register_error_handlers(app: Flask) -> None:
    """
    Register custom error handlers.
    
    Args:
        app: Flask application
    """
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit exceeded errors."""
        return create_error_response(
            ErrorCategory.RATE_LIMITED,
            f"Rate limit exceeded: {e.description}",
            status_code=429,
        )
    
    @app.errorhandler(RateLimitExceededError)
    def rate_limit_exceeded_handler(e):
        """Handle RateLimitExceededError with proper headers."""
        from flask import jsonify
        from datetime import datetime
        
        headers = {}
        if hasattr(e, 'rate_limit_context') and e.rate_limit_context:
            context = e.rate_limit_context
            if 'limit' in context:
                headers['X-RateLimit-Limit'] = str(context['limit'])
            if 'reset_at' in context:
                reset_at = context['reset_at']
                if isinstance(reset_at, str):
                    reset_dt = datetime.fromisoformat(reset_at.replace('Z', '+00:00'))
                    headers['X-RateLimit-Reset'] = str(int(reset_dt.timestamp()))
                elif isinstance(reset_at, datetime):
                    headers['X-RateLimit-Reset'] = str(int(reset_at.timestamp()))
            headers['X-RateLimit-Remaining'] = '0'
            
            response_data = {
                'error': 'Rate limit exceeded',
                'limit_type': context.get('limit_type'),
                'reset_at': context.get('reset_at')
            }
        else:
            response_data = {
                'error': 'Rate limit exceeded',
                'limit_type': None,
                'reset_at': None
            }
        
        response = jsonify(response_data)
        response.status_code = 429
        for key, value in headers.items():
            response.headers[key] = value
        return response


def _initialize_infrastructure(app: Flask, config: AppConfig) -> None:
    """
    Initialize infrastructure components (Redis, Celery, GCS, SocketIO).
    
    Args:
        app: Flask application
        config: Application configuration
    """
    try:
        # Initialize Redis
        init_redis()
        print("Redis initialized successfully")
        
        # Initialize Celery
        celery = make_celery(app)
        app.celery = celery
        print("Celery initialized successfully")
        
        # Initialize GCS (optional)
        gcs_initialized = init_gcs()
        if gcs_initialized:
            print("GCS initialized successfully")
        else:
            print("GCS not configured - using local file serving")
        
        # Initialize SocketIO (optional)
        socketio = None
        if config.socketio_enabled:
            try:
                socketio = init_socketio(app)
                app.socketio = socketio
                register_socketio_events(app)
                print("SocketIO initialized successfully")
            except Exception as e:
                print(f"Warning: Could not initialize SocketIO: {e}")
                print("WebSocket support disabled - using polling fallback")
        else:
            print("SocketIO disabled - using polling fallback")
        
    except Exception as e:
        print(f"Warning: Could not initialize infrastructure: {e}")
        app.celery = None


def _initialize_services(app: Flask) -> None:
    """
    Initialize application services and attach to app context using DependencyContainer.
    
    Args:
        app: Flask application
    """
    try:
        # Create dependency container
        container = DependencyContainer()
        
        # Initialize Redis
        redis_repo = get_redis_repository()
        
        # Register infrastructure components (Redis, repositories)
        container.register_singleton(type(redis_repo), redis_repo)
        
        # Register repositories
        job_repository = RedisJobRepository(redis_repo)
        file_repository = RedisFileRepository(redis_repo)
        storage_repository = LocalFileStorageRepository("/tmp/ultra-dl")
        
        container.register_singleton(RedisJobRepository, job_repository)
        container.register_singleton(RedisFileRepository, file_repository)
        container.register_singleton(LocalFileStorageRepository, storage_repository)
        
        # Register cache service
        from infrastructure.redis_cache_service import RedisCacheService
        cache_service = RedisCacheService(redis_repo, default_ttl=300)
        container.register_singleton(RedisCacheService, cache_service)
        
        # Register infrastructure services
        metadata_extractor = VideoMetadataExtractor()
        container.register_singleton(VideoMetadataExtractor, metadata_extractor)
        
        # Register domain services (JobManager, FileManager, VideoProcessor)
        job_manager = JobManager(job_repository)
        file_manager = FileManager(file_repository, storage_repository)
        video_processor = VideoProcessor(metadata_extractor)
        signed_url_service = SignedUrlService()
        
        container.register_singleton(JobManager, job_manager)
        container.register_singleton(FileManager, file_manager)
        container.register_singleton(VideoProcessor, video_processor)
        container.register_singleton(SignedUrlService, signed_url_service)
        
        # Register storage repository using StorageFactory
        from infrastructure.storage_factory import StorageFactory
        from domain.file_storage.storage_repository import IFileStorageRepository
        storage_repository = StorageFactory.create_storage()
        container.register_singleton(IFileStorageRepository, storage_repository)
        
        # Register application services (EventPublisher, DownloadService)
        event_publisher = EventPublisher()
        container.register_singleton(EventPublisher, event_publisher)
        
        download_service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_repository,
            event_publisher
        )
        container.register_singleton(DownloadService, download_service)
        
        # Register legacy JobService for backward compatibility
        job_service = JobService(job_manager, file_manager)
        container.register_singleton(JobService, job_service)
        
        # Register VideoService with video processor and cache service
        video_service = VideoService(video_processor=video_processor, cache_service=cache_service)
        container.register_singleton(VideoService, video_service)
        
        # Register rate limiting services
        # 1. Create RateLimitConfig singleton from environment
        rate_limit_config = RateLimitConfig.from_env()
        container.register_singleton(RateLimitConfig, rate_limit_config)
        
        # 2. Create RedisRateLimitRepository singleton with Redis client
        redis_client = get_redis_client()
        rate_limit_repository = RedisRateLimitRepository(redis_client, timeout=1)
        container.register_singleton(RedisRateLimitRepository, rate_limit_repository)
        
        # 3. Create RateLimitManager singleton with repository
        rate_limit_manager = RateLimitManager(rate_limit_repository)
        container.register_singleton(RateLimitManager, rate_limit_manager)
        
        # 4. Create RateLimitService singleton with manager and config
        rate_limit_service = RateLimitService(rate_limit_manager, rate_limit_config)
        container.register_singleton(RateLimitService, rate_limit_service)
        
        # Register event handlers and subscribe to events
        ws_handler = WebSocketEventHandler()
        event_publisher.subscribe(JobStartedEvent, ws_handler.handle_job_started)
        event_publisher.subscribe(JobProgressUpdatedEvent, ws_handler.handle_job_progress)
        event_publisher.subscribe(JobCompletedEvent, ws_handler.handle_job_completed)
        event_publisher.subscribe(JobFailedEvent, ws_handler.handle_job_failed)
        
        # Attach container to Flask app context
        app.container = container
        
        # Maintain backward compatibility by attaching services directly
        app.job_service = job_service
        app.file_manager = file_manager
        app.signed_url_service = signed_url_service
        app.rate_limit_service = rate_limit_service
        
        print("Application services initialized successfully with DependencyContainer")
        print(f"  - Registered {len(container._singletons)} singleton services")
        print(f"  - Registered {len(event_publisher._handlers)} event handler types")
        
        # Log rate limiting status
        if rate_limit_config.should_enforce():
            print(f"Rate limiting ENABLED (production mode)")
            print(f"  - Video-only daily: {rate_limit_config.video_only_daily}")
            print(f"  - Audio-only daily: {rate_limit_config.audio_only_daily}")
            print(f"  - Video-audio daily: {rate_limit_config.video_audio_daily}")
            print(f"  - Total jobs daily: {rate_limit_config.total_jobs_daily}")
            print(f"  - Batch per minute: {rate_limit_config.batch_per_minute}")
            print(f"  - Whitelisted IPs: {len(rate_limit_config.whitelist)}")
        else:
            print("Rate limiting DISABLED (development mode or disabled in config)")
        
    except Exception as e:
        print(f"Warning: Could not initialize services: {e}")
        app.container = None
        app.job_service = None
        app.file_manager = None
        app.signed_url_service = None


def _register_blueprints(app: Flask, config: AppConfig) -> None:
    """
    Register API blueprints and configure rate limits.
    
    Args:
        app: Flask application
        config: Application configuration
    """
    from api.v1 import api_v1_bp
    
    app.register_blueprint(api_v1_bp)
    
    # Apply specific rate limits to API endpoints (only in production)
    if config.is_production:
        try:
            app.limiter.limit("20 per minute")(
                app.view_functions[f"api_{config.api_version}.videos_video_resolutions"]
            )
            app.limiter.limit("10 per minute")(
                app.view_functions[f"api_{config.api_version}.downloads_download"]
            )
            app.limiter.limit("30 per minute")(
                app.view_functions[f"api_{config.api_version}.jobs_job"]
            )
            print("Specific rate limits applied to API endpoints")
        except KeyError as e:
            print(f"Warning: Could not apply rate limits to some endpoints: {e}")
    else:
        print("Skipping rate limit configuration (development mode)")
    
    print(f"API {config.api_version} registered at /api/{config.api_version} "
          f"with Swagger UI at /api/{config.api_version}/docs")


def _register_health_endpoint(app: Flask, limiter: Limiter) -> None:
    """
    Register health check endpoint.
    
    Args:
        app: Flask application
        limiter: Rate limiter instance
    """
    @app.route("/health", methods=["GET"])
    @limiter.exempt
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
        if hasattr(app, 'celery') and app.celery is not None:
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
