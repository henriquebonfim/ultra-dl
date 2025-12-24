"""
Unit tests for API REST endpoints.

Tests the API layer endpoints with mocked application services.
Validates request handling, response formatting, and status codes.

Requirements: 10.1, 10.3, 10.4
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask_restx import Api

from src.api.v1 import api as api_v1
from src.api.v1.namespaces import video_ns, job_ns, download_ns
from src.domain.errors import (
    ErrorCategory,
    InvalidUrlError,
    MetadataExtractionError,
    ApplicationError,
)
from src.domain.job_management import JobNotFoundError


@pytest.fixture
def flask_app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    # Initialize API
    api = Api(app, version='1.0', title='UltraDL API', doc='/doc')
    api.add_namespace(video_ns, path='/api/v1/videos')
    api.add_namespace(job_ns, path='/api/v1/jobs')
    api.add_namespace(download_ns, path='/api/v1/downloads')
    
    return app


@pytest.fixture
def client(flask_app):
    """Create test client."""
    return flask_app.test_client()


@pytest.fixture
def mock_video_service():
    """Mock VideoService for testing."""
    service = Mock()
    service.validate_url.return_value = True
    service.get_video_info.return_value = {
        "meta": {
            "id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 180,
            "thumbnail": "https://example.com/thumb.jpg",
        },
        "formats": [
            {
                "format_id": "137",
                "ext": "mp4",
                "resolution": "1920x1080",
                "height": 1080,
                "note": "1080p",
                "filesize": 50000000,
                "vcodec": "avc1",
                "acodec": "none",
                "quality_label": "Great",
                "type": "video_only",
            }
        ],
    }
    return service


@pytest.fixture
def mock_job_service():
    """Mock JobService for testing."""
    service = Mock()
    service.create_download_job.return_value = {
        "job_id": "test-job-123",
        "status": "pending",
        "message": "Job created successfully",
    }
    service.get_job_status.return_value = {
        "job_id": "test-job-123",
        "status": "processing",
        "progress": {
            "percentage": 50,
            "phase": "downloading",
            "speed": "1.5 MB/s",
            "eta": "30s",
        },
    }
    service.delete_job.return_value = True
    return service


@pytest.fixture
def mock_container(mock_video_service):
    """Mock DependencyContainer."""
    container = Mock()
    container.resolve.side_effect = lambda cls: {
        'VideoService': mock_video_service,
    }.get(cls.__name__, Mock())
    return container


# =============================================================================
# Test POST /api/v1/videos/resolutions
# =============================================================================

def test_get_resolutions_with_valid_url(client, flask_app, mock_container, mock_video_service):
    """
    Test GET resolutions endpoint with valid YouTube URL.
    
    Validates: Requirements 10.1, 10.3
    """
    flask_app.container = mock_container
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert "meta" in data
    assert "formats" in data
    assert data["meta"]["id"] == "dQw4w9WgXcQ"
    assert len(data["formats"]) > 0


def test_get_resolutions_with_empty_url(client, flask_app, mock_container):
    """
    Test GET resolutions endpoint with empty URL returns 400.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": ""},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert data["error"] == ErrorCategory.INVALID_REQUEST.value


def test_get_resolutions_with_invalid_url(client, flask_app, mock_container, mock_video_service):
    """
    Test GET resolutions endpoint with invalid URL returns 400.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    mock_video_service.get_video_info.side_effect = InvalidUrlError("Invalid YouTube URL")
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": "https://example.com/not-youtube"},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert data["error"] == ErrorCategory.INVALID_URL.value


def test_get_resolutions_with_unavailable_video(client, flask_app, mock_container, mock_video_service):
    """
    Test GET resolutions endpoint with unavailable video returns 400.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    mock_video_service.get_video_info.side_effect = MetadataExtractionError("Video unavailable")
    mock_video_service._categorize_extraction_error.return_value = ErrorCategory.VIDEO_UNAVAILABLE
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": "https://www.youtube.com/watch?v=invalid"},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


# =============================================================================
# Test GET /api/v1/jobs/{job_id}
# =============================================================================

def test_get_job_status_success(client, flask_app, mock_job_service):
    """
    Test GET job status endpoint returns job information.
    
    Validates: Requirements 10.1, 10.3
    """
    flask_app.job_service = mock_job_service
    
    response = client.get('/api/v1/jobs/test-job-123')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["job_id"] == "test-job-123"
    assert data["status"] == "processing"
    assert "progress" in data


def test_get_job_status_not_found(client, flask_app, mock_job_service):
    """
    Test GET job status endpoint returns 404 for non-existent job.
    
    Validates: Requirements 10.1
    """
    flask_app.job_service = mock_job_service
    mock_job_service.get_job_status.side_effect = JobNotFoundError("Job not found")
    
    response = client.get('/api/v1/jobs/nonexistent-job')
    
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == ErrorCategory.JOB_NOT_FOUND.value


def test_get_job_status_service_unavailable(client, flask_app):
    """
    Test GET job status endpoint returns 503 when service not initialized.
    
    Validates: Requirements 10.1
    """
    flask_app.job_service = None
    
    response = client.get('/api/v1/jobs/test-job-123')
    
    assert response.status_code == 503
    data = response.get_json()
    assert "error" in data


# =============================================================================
# Test POST /api/v1/downloads/
# =============================================================================

def test_create_download_with_valid_request(client, flask_app, mock_container, mock_job_service, mock_video_service):
    """
    Test POST download endpoint with valid request creates job.
    
    Validates: Requirements 10.1, 10.3
    """
    flask_app.container = mock_container
    flask_app.job_service = mock_job_service
    flask_app.celery = Mock()
    flask_app.celery.send_task.return_value = Mock()
    
    response = client.post(
        '/api/v1/downloads/',
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format_id": "137"
        },
        content_type='application/json'
    )
    
    assert response.status_code == 202
    data = response.get_json()
    assert data["job_id"] == "test-job-123"
    assert data["status"] == "pending"
    
    # Verify Celery task was enqueued
    flask_app.celery.send_task.assert_called_once()


def test_create_download_missing_url(client, flask_app, mock_container):
    """
    Test POST download endpoint with missing URL returns 400.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    
    response = client.post(
        '/api/v1/downloads/',
        json={"format_id": "137"},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    # Flask-RESTX validation returns different format
    assert "errors" in data or "error" in data


def test_create_download_missing_format_id(client, flask_app, mock_container, mock_job_service, mock_video_service):
    """
    Test POST download endpoint with missing format_id still creates job with 'auto' format.
    
    The endpoint accepts missing format_id and defaults to 'auto' format selection.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    flask_app.job_service = mock_job_service
    flask_app.celery = Mock()
    flask_app.celery.send_task.return_value = Mock()
    
    response = client.post(
        '/api/v1/downloads/',
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        content_type='application/json'
    )
    
    # The endpoint accepts missing format_id and uses 'auto' as default
    assert response.status_code == 202
    data = response.get_json()
    assert data["job_id"] == "test-job-123"


def test_create_download_invalid_url(client, flask_app, mock_container, mock_video_service):
    """
    Test POST download endpoint with invalid URL returns 400.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    flask_app.job_service = Mock()
    mock_video_service.validate_url.return_value = False
    
    response = client.post(
        '/api/v1/downloads/',
        json={
            "url": "https://example.com/not-youtube",
            "format_id": "137"
        },
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    # Check for error in response (may be in different formats)
    assert "error" in data or "message" in data


def test_create_download_celery_unavailable(client, flask_app, mock_container, mock_job_service, mock_video_service):
    """
    Test POST download endpoint returns 503 when Celery unavailable.
    
    Validates: Requirements 10.1
    """
    flask_app.container = mock_container
    flask_app.job_service = mock_job_service
    flask_app.celery = None
    
    response = client.post(
        '/api/v1/downloads/',
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format_id": "137"
        },
        content_type='application/json'
    )
    
    assert response.status_code == 503
    data = response.get_json()
    # Check for error in response (may be in different formats)
    assert "error" in data or "message" in data


# =============================================================================
# Test Rate Limit Headers
# =============================================================================

# =============================================================================
# Test DELETE /api/v1/jobs/{job_id}
# =============================================================================

def test_delete_job_success(client, flask_app, mock_job_service):
    """
    Test DELETE job endpoint successfully deletes job.
    
    Validates: Requirements 10.1
    """
    flask_app.job_service = mock_job_service
    mock_job_service.get_job_status.return_value = {
        "job_id": "test-job-123",
        "status": "completed"
    }
    
    response = client.delete('/api/v1/jobs/test-job-123')
    
    assert response.status_code == 204
    mock_job_service.delete_job.assert_called_once_with("test-job-123")


def test_delete_job_not_found(client, flask_app, mock_job_service):
    """
    Test DELETE job endpoint returns 404 for non-existent job.
    
    Validates: Requirements 10.1
    """
    flask_app.job_service = mock_job_service
    mock_job_service.get_job_status.side_effect = JobNotFoundError("Job not found")
    
    response = client.delete('/api/v1/jobs/nonexistent-job')
    
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
