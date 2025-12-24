"""
Unit tests for API error mapping.

Tests that ApplicationError categories are correctly mapped to HTTP status codes
and that error responses have the correct JSON structure.

Requirements: 10.2, 14.3, 14.4
"""

import pytest
from unittest.mock import Mock
from flask import Flask
from flask_restx import Api

from src.api.v1 import api as api_v1
from src.api.v1.namespaces import video_ns, job_ns, download_ns
from src.domain.errors import (
    ErrorCategory,
    InvalidUrlError,
    MetadataExtractionError,
    ApplicationError,
    create_error_response,
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
def mock_container():
    """Mock DependencyContainer."""
    container = Mock()
    video_service = Mock()
    video_service.validate_url.return_value = True
    
    # Mock rate limit service to return None (no rate limiting)
    rate_limit_service = Mock()
    rate_limit_service.check_endpoint_limit.return_value = None
    
    def resolve_service(cls):
        if cls.__name__ == 'VideoService':
            return video_service
        elif cls.__name__ == 'RateLimitService':
            return rate_limit_service
        return Mock()
    
    container.resolve.side_effect = resolve_service
    return container


# =============================================================================
# Test 400 Bad Request - Validation Errors
# =============================================================================

def test_validation_error_returns_400(client, flask_app, mock_container):
    """
    Test that validation errors return HTTP 400.
    
    Validates: Requirements 10.2, 14.3
    """
    flask_app.container = mock_container
    
    # Missing required field
    response = client.post(
        '/api/v1/videos/resolutions',
        json={},
        content_type='application/json'
    )
    
    assert response.status_code == 400


def test_invalid_url_returns_400(client, flask_app, mock_container):
    """
    Test that invalid URL errors return HTTP 400.
    
    Validates: Requirements 10.2, 14.3
    """
    flask_app.container = mock_container
    
    # Update the video service mock to raise InvalidUrlError
    video_service = Mock()
    video_service.get_video_info.side_effect = InvalidUrlError("Invalid URL")
    
    # Update container to return the configured video service
    def resolve_service(cls):
        if cls.__name__ == 'VideoService':
            return video_service
        elif cls.__name__ == 'RateLimitService':
            rate_limit_service = Mock()
            rate_limit_service.check_endpoint_limit.return_value = None
            return rate_limit_service
        return Mock()
    
    flask_app.container.resolve.side_effect = resolve_service
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": "https://example.com/invalid"},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == ErrorCategory.INVALID_URL.value


def test_invalid_request_returns_400(client, flask_app, mock_container):
    """
    Test that invalid request errors return HTTP 400.
    
    Validates: Requirements 10.2, 14.3
    """
    flask_app.container = mock_container
    
    # Empty URL
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": ""},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == ErrorCategory.INVALID_REQUEST.value


# =============================================================================
# Test 404 Not Found
# =============================================================================

def test_job_not_found_returns_404(client, flask_app):
    """
    Test that job not found errors return HTTP 404.
    
    Validates: Requirements 10.2, 14.3
    """
    job_service = Mock()
    job_service.get_job_status.side_effect = JobNotFoundError("Job not found")
    flask_app.job_service = job_service
    
    response = client.get('/api/v1/jobs/nonexistent-job')
    
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == ErrorCategory.JOB_NOT_FOUND.value


def test_job_not_found_on_delete_returns_404(client, flask_app):
    """
    Test that deleting non-existent job returns HTTP 404.
    
    Validates: Requirements 10.2, 14.3
    """
    job_service = Mock()
    job_service.get_job_status.side_effect = JobNotFoundError("Job not found")
    flask_app.job_service = job_service
    
    response = client.delete('/api/v1/jobs/nonexistent-job')
    
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == ErrorCategory.JOB_NOT_FOUND.value


# =============================================================================
# Test 410 Gone - Expired Resources
# =============================================================================

def test_file_expired_returns_410(client, flask_app):
    """
    Test that expired file errors return HTTP 410.
    
    Validates: Requirements 10.2, 14.3
    """
    from src.domain.file_storage.services import FileExpiredError
    
    # Mock file manager that raises FileExpiredError
    file_manager = Mock()
    file_manager.get_file_by_token.side_effect = FileExpiredError("File expired")
    flask_app.file_manager = file_manager
    
    response = client.get('/api/v1/downloads/file/expired-token')
    
    assert response.status_code == 410
    data = response.get_json()
    assert data["error"] == ErrorCategory.FILE_EXPIRED.value


# =============================================================================



# =============================================================================
# Test 500 Internal Server Error - System Errors
# =============================================================================

def test_system_error_returns_500(client, flask_app, mock_container):
    """
    Test that system errors return HTTP 500.
    
    Validates: Requirements 10.2, 14.3
    """
    flask_app.container = mock_container
    
    # Update the video service mock to raise Exception
    video_service = Mock()
    video_service.get_video_info.side_effect = Exception("Unexpected error")
    
    # Update container to return the configured video service
    def resolve_service(cls):
        if cls.__name__ == 'VideoService':
            return video_service
        elif cls.__name__ == 'RateLimitService':
            rate_limit_service = Mock()
            rate_limit_service.check_endpoint_limit.return_value = None
            return rate_limit_service
        return Mock()
    
    flask_app.container.resolve.side_effect = resolve_service
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": "https://www.youtube.com/watch?v=test"},
        content_type='application/json'
    )
    
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == ErrorCategory.SYSTEM_ERROR.value


def test_service_unavailable_returns_503(client, flask_app):
    """
    Test that service unavailable errors return HTTP 503.
    
    Validates: Requirements 10.2, 14.3
    """
    flask_app.job_service = None
    
    response = client.get('/api/v1/jobs/test-job')
    
    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] == ErrorCategory.SYSTEM_ERROR.value


# =============================================================================
# Test Error Response JSON Structure
# =============================================================================

def test_error_response_has_required_fields(client, flask_app, mock_container):
    """
    Test that error responses have the required JSON structure.
    
    Validates: Requirements 10.2, 14.4
    """
    flask_app.container = mock_container
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": ""},
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    
    # Check required fields (error response from create_error_response)
    assert "error" in data
    assert "title" in data
    assert "message" in data
    assert "action" in data


def test_error_response_has_user_friendly_message(client, flask_app, mock_container):
    """
    Test that error responses contain user-friendly messages.
    
    Validates: Requirements 14.4
    """
    flask_app.container = mock_container
    
    # Update the video service mock to raise InvalidUrlError
    video_service = Mock()
    video_service.get_video_info.side_effect = InvalidUrlError("Invalid URL")
    
    # Update container to return the configured video service
    def resolve_service(cls):
        if cls.__name__ == 'VideoService':
            return video_service
        elif cls.__name__ == 'RateLimitService':
            rate_limit_service = Mock()
            rate_limit_service.check_endpoint_limit.return_value = None
            return rate_limit_service
        return Mock()
    
    flask_app.container.resolve.side_effect = resolve_service
    
    response = client.post(
        '/api/v1/videos/resolutions',
        json={"url": "https://example.com/invalid"},
        content_type='application/json'
    )
    
    data = response.get_json()
    
    # Check that message is user-friendly (not technical)
    assert "title" in data
    assert "message" in data
    assert "action" in data
    assert len(data["message"]) > 0
    assert len(data["action"]) > 0


def test_error_response_does_not_leak_technical_details():
    """
    Test that error responses don't leak technical details.
    
    Validates: Requirements 14.4
    """
    # Create error response
    response_data, status_code = create_error_response(
        ErrorCategory.SYSTEM_ERROR,
        technical_message="Database connection failed at line 42 in db.py",
        status_code=500
    )
    
    # Technical message should not be in response
    assert "Database connection failed" not in str(response_data)
    assert "line 42" not in str(response_data)
    assert "db.py" not in str(response_data)
    
    # Should have user-friendly message instead
    assert "error" in response_data
    assert "title" in response_data
    assert "message" in response_data


# =============================================================================
# Test Error Category to HTTP Status Mapping
# =============================================================================

def test_error_category_mapping():
    """
    Test that error categories map to correct HTTP status codes.
    
    Validates: Requirements 10.2, 14.3
    """
    # Test validation errors -> 400
    _, status = create_error_response(ErrorCategory.INVALID_URL, status_code=400)
    assert status == 400
    
    _, status = create_error_response(ErrorCategory.INVALID_REQUEST, status_code=400)
    assert status == 400
    
    # Test not found -> 404
    _, status = create_error_response(ErrorCategory.JOB_NOT_FOUND, status_code=404)
    assert status == 404
    
    _, status = create_error_response(ErrorCategory.FILE_NOT_FOUND, status_code=404)
    assert status == 404
    
    # Test expired -> 410
    _, status = create_error_response(ErrorCategory.FILE_EXPIRED, status_code=410)
    assert status == 410
    
    # Test system errors -> 500
    _, status = create_error_response(ErrorCategory.SYSTEM_ERROR, status_code=500)
    assert status == 500


def test_application_error_to_dict():
    """
    Test that ApplicationError converts to dict correctly.
    
    Validates: Requirements 14.4
    """
    error = ApplicationError(
        ErrorCategory.INVALID_URL,
        technical_message="URL validation failed",
        context={"url": "https://example.com"}
    )
    
    error_dict = error.to_dict()
    
    assert "error" in error_dict
    assert "title" in error_dict
    assert "message" in error_dict
    assert "action" in error_dict
    assert error_dict["error"] == ErrorCategory.INVALID_URL.value
    
    # Technical message should not be in dict
    assert "URL validation failed" not in str(error_dict)
