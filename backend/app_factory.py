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
from src.api.websocket_events import register_socketio_events
from src.application.dependency_container import DependencyContainer
from src.application.download_service import DownloadService
from src.application.job_service import JobService
from src.application.video_service import VideoService
from src.config.celery_config import make_celery
from src.config.redis_config import (
    get_redis_client,
    get_redis_repository,
    init_redis,
    redis_health_check,
)
from src.config.socketio_config import init_socketio, is_socketio_enabled
from src.domain.file_storage import FileManager, SignedUrlService
from src.domain.job_management import JobManager
from src.domain.video_processing.services import VideoProcessor
from src.infrastructure.local_file_storage_repository import LocalFileStorageRepository
from src.infrastructure.redis_file_repository import RedisFileRepository
from src.infrastructure.redis_job_archive_repository import RedisJobArchiveRepository
from src.infrastructure.redis_job_repository import RedisJobRepository
from src.infrastructure.video_metadata_extractor import VideoMetadataExtractor


class AppConfig:
    """Application configuration."""

    def __init__(self):
        self.api_version = os.getenv("API_VERSION", "v1")
        self.flask_env = os.getenv("FLASK_ENV", "development")
        self.is_production = self.flask_env == "production"

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
    CORS(
        app,
        resources={
            r"/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
                "expose_headers": ["Content-Type", "X-Total-Count"],
                "supports_credentials": True,
                "max_age": 3600,
            }
        },
    )

    # Initialize infrastructure
    _initialize_infrastructure(app, config)

    # Initialize services
    _initialize_services(app)

    # Register blueprints
    _register_blueprints(app, config)

    # Register health check endpoint
    _register_health_endpoint(app)

    return app


def _initialize_infrastructure(app: Flask, config: AppConfig) -> None:
    """
    Initialize infrastructure components (Redis, Celery, SocketIO).

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

    This is the SINGLE dependency injection pattern used throughout the application (Requirement 1.5).
    All services are registered here as singletons and resolved via container.resolve() in API/tasks.

    PATTERN:
    --------
    1. Create DependencyContainer instance
    2. Register all infrastructure adapters (repositories, external services)
    3. Register all domain services (managers, processors)
    4. Register all application services (orchestrators)
    5. Attach container to Flask app context for global access

    NO OTHER DI PATTERNS (like ServiceLocator) should be used in this codebase.

    Args:
        app: Flask application
    """
    try:
        # Create dependency container (SINGLE DI pattern - Requirement 1.5)
        container = DependencyContainer()

        # Initialize Redis
        redis_repo = get_redis_repository()

        # Register infrastructure components (Redis, repositories)
        container.register_singleton(type(redis_repo), redis_repo)

        # Register repositories
        job_repository = RedisJobRepository(redis_repo)
        file_repository = RedisFileRepository(redis_repo)
        storage_repository = LocalFileStorageRepository("/tmp/ultra-dl")

        # Register job archive repository
        redis_client = get_redis_client()
        job_archive_repository = RedisJobArchiveRepository(redis_client)

        container.register_singleton(RedisJobRepository, job_repository)
        container.register_singleton(RedisFileRepository, file_repository)
        container.register_singleton(LocalFileStorageRepository, storage_repository)
        container.register_singleton(RedisJobArchiveRepository, job_archive_repository)

        # Register repository interfaces for dependency resolution
        from src.domain.job_management.repositories import IJobArchiveRepository

        container.register_singleton(IJobArchiveRepository, job_archive_repository)

        # Register cache service
        from src.infrastructure.redis_cache_service import RedisCacheService

        cache_service = RedisCacheService(redis_repo, default_ttl=300)
        container.register_singleton(RedisCacheService, cache_service)

        # Register infrastructure services
        metadata_extractor = VideoMetadataExtractor()
        container.register_singleton(VideoMetadataExtractor, metadata_extractor)

        # Register domain services (JobManager, FileManager, VideoProcessor)
        job_manager = JobManager(job_repository, job_archive_repository)
        file_manager = FileManager(file_repository, storage_repository)
        video_processor = VideoProcessor(metadata_extractor)
        signed_url_service = SignedUrlService()

        container.register_singleton(JobManager, job_manager)
        container.register_singleton(FileManager, file_manager)
        container.register_singleton(VideoProcessor, video_processor)
        container.register_singleton(SignedUrlService, signed_url_service)

        # Register storage repository using StorageFactory
        from src.domain.file_storage.storage_repository import IFileStorageRepository
        from src.infrastructure.storage_factory import StorageFactory

        storage_repository = StorageFactory.create_storage()
        container.register_singleton(IFileStorageRepository, storage_repository)

        # Register application services
        #
        # Service Purpose Distinction:
        # - DownloadService: Orchestrates the full download workflow (video extraction,
        #   file download, storage). Used by Celery background tasks for async processing.
        # - JobService: Handles job lifecycle CRUD operations (create, update, query, cleanup).
        #   Used by API layer and WebSocket events for job state management.
        #
        # Both services serve legitimate separate purposes without duplication.

        download_service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_repository,
        )
        container.register_singleton(DownloadService, download_service)

        job_service = JobService(job_manager, file_manager)
        container.register_singleton(JobService, job_service)

        # Register VideoService with video processor and cache service
        video_service = VideoService(
            video_processor=video_processor, cache_service=cache_service
        )
        container.register_singleton(VideoService, video_service)

        # Attach container to Flask app context
        app.container = container

        # Attach commonly-used services directly to app for convenient access
        # This is the primary pattern for service access in API routes and tasks
        app.job_service = job_service
        app.file_manager = file_manager
        app.signed_url_service = signed_url_service

        print("Application services initialized successfully with DependencyContainer")
        print(f"  - Registered {len(container._singletons)} singleton services")

    except Exception as e:
        print(f"Warning: Could not initialize services: {e}")
        app.container = None
        app.job_service = None
        app.file_manager = None
        app.signed_url_service = None


def _register_blueprints(app: Flask, config: AppConfig) -> None:
    """
    Register API blueprints.

    Args:
        app: Flask application
        config: Application configuration
    """
    from src.api.v1 import api_v1_bp

    app.register_blueprint(api_v1_bp)

    print(
        f"API {config.api_version} registered at /api/{config.api_version} "
        f"with Swagger UI at /api/{config.api_version}/docs"
    )


def _get_health_status(app: Flask) -> tuple[dict, int]:
    """
    Get health status of all system components.

    Checks Redis, Celery, and SocketIO availability and returns a
    comprehensive health status dictionary with appropriate HTTP status code.

    Args:
        app: Flask application instance

    Returns:
        Tuple of (health_status_dict, http_status_code)
    """
    health_status = {
        "status": "ok",
        "message": "backend ready",
        "redis": "unknown",
        "celery": "unknown",
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
    if hasattr(app, "celery") and app.celery is not None:
        health_status["celery"] = "available"
    else:
        health_status["celery"] = "unavailable"
        health_status["status"] = "degraded"

    # Check SocketIO availability (optional - not critical)
    if is_socketio_enabled():
        health_status["socketio"] = "available"
    else:
        health_status["socketio"] = "not_configured"

    status_code = 200 if health_status["status"] == "ok" else 503
    return health_status, status_code


def _register_health_endpoint(app: Flask) -> None:
    """
    Register health check endpoint.

    Args:
        app: Flask application
    """

    @app.route("/health", methods=["GET"])
    def health():
        """
        Health check endpoint.
        Returns overall health status of the application and its dependencies.
        """
        health_status, status_code = _get_health_status(app)
        return jsonify(health_status), status_code
