"""
Test Configuration and Shared Fixtures

This module provides shared pytest fixtures and configuration for all backend tests.
Fixtures are organized by category and follow the test isolation principle.

Fixture Categories:
- Application Context: Flask app instances and contexts
- Infrastructure: Redis, storage, and external service mocks
- Domain Entities: Sample jobs, files, and domain objects
- Test Data: Builders and factories for test data generation
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Generator
from unittest.mock import Mock

import fakeredis
import pytest
from app_factory import AppConfig, create_app
from domain.file_storage.entities import DownloadedFile
from domain.file_storage.value_objects import DownloadToken
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobProgress, JobStatus
from flask import Flask

# ============================================================================
# Application Context Fixtures
# ============================================================================


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """
    Create a Flask application instance for testing.

    Provides a fully configured Flask app with test configuration:
    - Testing mode enabled
    - Temporary storage directory
    - Fake Redis for isolation
    - All services initialized

    Yields:
        Flask: Configured Flask application instance

    Example:
        def test_endpoint(app):
            with app.test_client() as client:
                response = client.get('/api/v1/health')
                assert response.status_code == 200
    """
    config = AppConfig()
    config.is_production = False
    test_app = create_app(config)

    yield test_app

    # Cleanup is handled by app teardown


@pytest.fixture
def client(app):
    """
    Create a Flask test client for API testing.

    Provides a test client that can make HTTP requests to the application
    without running a real server.

    Args:
        app: Flask application fixture

    Returns:
        FlaskClient: Test client for making requests

    Example:
        def test_api_endpoint(client):
            response = client.post('/api/v1/downloads/', json={
                'url': 'https://youtube.com/watch?v=test',
                'format_id': '22'
            })
            assert response.status_code == 202
    """
    return app.test_client()


@pytest.fixture
def app_context(app):
    """
    Create a Flask application context for testing.

    Provides an active application context for tests that need to access
    Flask's current_app or use service locators.

    Args:
        app: Flask application fixture

    Yields:
        Flask app context

    Example:
        def test_container_access(app_context):
            from flask import current_app
            from application.job_service import JobService
            job_service = current_app.container.resolve(JobService)
            assert job_service is not None
    """
    with app.app_context():
        yield


# ============================================================================
# Infrastructure Fixtures
# ============================================================================


@pytest.fixture
def redis_client():
    """
    Create a fake Redis client for testing.

    Provides an in-memory Redis implementation using fakeredis.
    Automatically flushed before and after each test for isolation.

    Returns:
        FakeRedis: In-memory Redis client

    Example:
        def test_redis_operations(redis_client):
            redis_client.set('key', 'value')
            assert redis_client.get('key') == b'value'
    """
    client = fakeredis.FakeRedis()
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """
    Create a temporary storage directory for file operations.

    Provides an isolated temporary directory for testing file storage.
    Automatically cleaned up after the test completes.

    Yields:
        str: Path to temporary storage directory

    Example:
        def test_file_storage(temp_storage_dir):
            file_path = os.path.join(temp_storage_dir, 'test.mp4')
            with open(file_path, 'w') as f:
                f.write('test content')
            assert os.path.exists(file_path)
    """
    temp_dir = tempfile.mkdtemp(prefix="ultra-dl-test-")
    yield temp_dir

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_socketio():
    """
    Create a mock SocketIO instance for WebSocket testing.

    Provides a mock SocketIO object with tracked method calls for
    testing WebSocket event emission without a real connection.

    Returns:
        Mock: Mock SocketIO instance

    Example:
        def test_websocket_emit(mock_socketio):
            from api.websocket_events import emit_job_progress
            emit_job_progress('job-123', {'percentage': 50})
            mock_socketio.emit.assert_called_once()
    """
    mock = Mock()
    mock.emit = Mock()
    mock.join_room = Mock()
    mock.leave_room = Mock()
    return mock


# ============================================================================
# Domain Entity Fixtures
# ============================================================================


@pytest.fixture
def sample_job() -> DownloadJob:
    """
    Create a sample DownloadJob entity for testing.

    Provides a basic job entity with common test values.
    Use job builders for more complex scenarios.

    Returns:
        DownloadJob: Sample job in PENDING status

    Example:
        def test_job_service(sample_job):
            assert sample_job.status == JobStatus.PENDING
            assert sample_job.url == 'https://youtube.com/watch?v=test123'
    """
    return DownloadJob(
        job_id="test-job-123",
        url="https://youtube.com/watch?v=test123",
        format_id="22",
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_progress() -> JobProgress:
    """
    Create a sample JobProgress entity for testing.

    Provides progress data representing a job at 50% completion.

    Returns:
        JobProgress: Sample progress at 50%

    Example:
        def test_progress_update(sample_progress):
            assert sample_progress.percentage == 50.0
            assert sample_progress.eta_seconds == 10
    """
    return JobProgress(
        percentage=50.0,
        downloaded_bytes=1024000,
        total_bytes=2048000,
        speed_bytes_per_sec=102400,
        eta_seconds=10,
    )


@pytest.fixture
def sample_file() -> DownloadedFile:
    """
    Create a sample DownloadedFile entity for testing.

    Provides a file entity with common test values.

    Returns:
        DownloadedFile: Sample file entity

    Example:
        def test_file_operations(sample_file):
            assert sample_file.job_id == 'test-job-123'
            assert sample_file.filesize == 1024000
    """
    return DownloadedFile.create(
        file_path="/tmp/ultra-dl/test-job-123/video.mp4",
        job_id="test-job-123",
        filename="video.mp4",
        ttl_minutes=15,
    )


@pytest.fixture
def sample_token() -> DownloadToken:
    """
    Create a sample DownloadToken for testing.

    Provides a valid download token for file access testing.

    Returns:
        DownloadToken: Sample download token

    Example:
        def test_token_validation(sample_token):
            assert len(str(sample_token)) >= 32
            assert sample_token.is_url_safe()
    """
    return DownloadToken.generate()


# ============================================================================
# Test Data Builders
# ============================================================================


class JobBuilder:
    """
    Builder pattern for creating test DownloadJob entities.

    Provides a fluent interface for constructing jobs with custom properties.
    Use this for complex test scenarios requiring specific job states.

    Example:
        def test_completed_job():
            job = (JobBuilder()
                   .with_id('custom-id')
                   .with_status(JobStatus.COMPLETED)
                   .with_file_path('/path/to/file.mp4')
                   .build())
            assert job.status == JobStatus.COMPLETED
    """

    def __init__(self):
        self._job_id = "test-job"
        self._url = "https://youtube.com/watch?v=test"
        self._format_id = "22"
        self._status = JobStatus.PENDING
        self._file_path = None
        self._error_message = None
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()

    def with_id(self, job_id: str):
        """Set custom job ID"""
        self._job_id = job_id
        return self

    def with_url(self, url: str):
        """Set custom URL"""
        self._url = url
        return self

    def with_format_id(self, format_id: str):
        """Set custom format ID"""
        self._format_id = format_id
        return self

    def with_status(self, status: JobStatus):
        """Set job status"""
        self._status = status
        return self

    def with_file_path(self, file_path: str):
        """Set file path (for completed jobs)"""
        self._file_path = file_path
        return self

    def with_error(self, error_message: str):
        """Set error message (for failed jobs)"""
        self._error_message = error_message
        return self

    def completed(self):
        """Shortcut to create a completed job"""
        self._status = JobStatus.COMPLETED
        self._file_path = f"/tmp/ultra-dl/{self._job_id}/video.mp4"
        return self

    def failed(self, error_message: str = "Test error"):
        """Shortcut to create a failed job"""
        self._status = JobStatus.FAILED
        self._error_message = error_message
        return self

    def build(self) -> DownloadJob:
        """Build the DownloadJob entity"""
        return DownloadJob(
            job_id=self._job_id,
            url=self._url,
            format_id=self._format_id,
            status=self._status,
            file_path=self._file_path,
            error_message=self._error_message,
            created_at=self._created_at,
            updated_at=self._updated_at,
        )


@pytest.fixture
def job_builder():
    """
    Provide a JobBuilder instance for test data creation.

    Returns:
        JobBuilder: Builder for creating custom jobs

    Example:
        def test_with_builder(job_builder):
            job = job_builder.with_id('custom').completed().build()
            assert job.status == JobStatus.COMPLETED
    """
    return JobBuilder()


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_job_repository():
    """
    Create a mock JobRepository for unit testing.

    Provides a mock repository with common method stubs.
    Configure return values as needed for specific tests.

    Returns:
        Mock: Mock JobRepository

    Example:
        def test_job_service(mock_job_repository):
            mock_job_repository.get.return_value = sample_job
            # Test code using the mock
    """
    mock = Mock()
    mock.save = Mock(return_value=True)
    mock.get = Mock(return_value=None)
    mock.delete = Mock(return_value=True)
    mock.exists = Mock(return_value=False)
    return mock


@pytest.fixture
def mock_file_repository():
    """
    Create a mock FileRepository for unit testing.

    Provides a mock repository for file storage operations.

    Returns:
        Mock: Mock FileRepository

    Example:
        def test_file_service(mock_file_repository):
            mock_file_repository.save_file.return_value = True
            # Test code using the mock
    """
    mock = Mock()
    mock.save_file = Mock(return_value=True)
    mock.delete_file = Mock(return_value=True)
    mock.file_exists = Mock(return_value=False)
    mock.get_file_size = Mock(return_value=1024000)
    return mock


@pytest.fixture
def mock_event_publisher():
    """
    Create a mock EventPublisher for unit testing.

    Provides a mock event publisher for testing domain event publication.

    Returns:
        Mock: Mock EventPublisher

    Example:
        def test_event_publishing(mock_event_publisher):
            service.publish_event(JobStartedEvent('job-123'))
            mock_event_publisher.publish.assert_called_once()
    """
    mock = Mock()
    mock.publish = Mock()
    mock.subscribe = Mock()
    return mock


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """
    Configure pytest with custom markers.

    Markers:
    - unit: Unit tests (fast, isolated)
    - integration: Integration tests (with external services)
    - e2e: End-to-end tests (full workflows)
    - performance: Performance and latency tests
    """
    config.addinivalue_line("markers", "unit: Unit tests with mocked dependencies")
    config.addinivalue_line(
        "markers", "integration: Integration tests with real services"
    )
    config.addinivalue_line("markers", "e2e: End-to-end workflow tests")
    config.addinivalue_line("markers", "performance: Performance and latency tests")


# ============================================================================
# Auto-use Fixtures (Applied to All Tests)
# ============================================================================


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Reset environment variables before each test.

    Ensures test isolation by clearing test-specific environment variables.
    Applied automatically to all tests.
    """
    # Store original environment
    original_env = os.environ.copy()

    # Set test defaults
    os.environ["FLASK_ENV"] = "development"
    os.environ["TESTING"] = "true"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
