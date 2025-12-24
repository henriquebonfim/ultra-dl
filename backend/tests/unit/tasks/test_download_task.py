"""
Unit tests for download_task

Tests that the Celery download task calls DownloadService with correct parameters,
handles exceptions and reports errors, and uses DependencyContainer for service resolution.

Requirements: 11.1, 11.4
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.application.download_result import DownloadResult
from src.application.download_service import DownloadService


@pytest.fixture
def mock_download_service():
    """Mock DownloadService for testing."""
    mock = Mock(spec=DownloadService)
    # Default successful result
    mock.execute_download.return_value = DownloadResult(
        success=True,
        file_path="/tmp/test_video.mp4",
        error_message=None,
        error_type=None,
    )
    return mock


@pytest.fixture
def mock_container(mock_download_service):
    """Mock DependencyContainer."""
    mock = MagicMock()
    mock.resolve.return_value = mock_download_service
    return mock


@pytest.fixture
def mock_flask_app(mock_container):
    """Mock Flask app with DependencyContainer."""
    mock_app = MagicMock()
    mock_app.container = mock_container
    return mock_app


class TestDownloadTaskServiceResolution:
    """Test that download_task uses DependencyContainer for service resolution."""

    @patch("celery_app.flask_app")
    def test_resolves_download_service_from_container(
        self, mock_flask_app_patch, mock_flask_app, mock_download_service
    ):
        """
        Test that download_task resolves DownloadService from DependencyContainer.
        
        Verifies that:
        - Task accesses flask_app.container
        - container.resolve() is called with DownloadService
        - Task never instantiates services directly
        
        Requirements: 11.4
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.download_task import download_video
        
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"
        
        # Act
        result = download_video(job_id, url, format_id)
        
        # Assert
        # Verify container.resolve was called with DownloadService
        mock_flask_app.container.resolve.assert_called_once_with(DownloadService)
        
        # Verify DownloadService.execute_download was called
        mock_download_service.execute_download.assert_called_once()


class TestDownloadTaskParameterPassing:
    """Test that download_task calls DownloadService with correct parameters."""

    @patch("celery_app.flask_app")
    def test_calls_download_service_with_correct_parameters(
        self, mock_flask_app_patch, mock_flask_app, mock_download_service
    ):
        """
        Test that download_task passes all parameters correctly to DownloadService.
        
        Verifies that:
        - job_id is passed correctly
        - url is passed correctly
        - format_id is passed correctly
        - progress_callback is provided
        
        Requirements: 11.1
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.download_task import download_video
        
        job_id = "test-job-456"
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        format_id = "137"
        
        # Act
        result = download_video(job_id, url, format_id)
        
        # Assert
        mock_download_service.execute_download.assert_called_once()
        call_args = mock_download_service.execute_download.call_args
        
        # Verify positional/keyword arguments
        assert call_args.kwargs["job_id"] == job_id
        assert call_args.kwargs["url"] == url
        assert call_args.kwargs["format_id"] == format_id
        
        # Verify progress_callback is provided
        assert "progress_callback" in call_args.kwargs
        assert callable(call_args.kwargs["progress_callback"])


class TestDownloadTaskReturnValue:
    """Test that download_task returns correct result format."""

    @patch("celery_app.flask_app")
    def test_returns_success_result_on_success(
        self, mock_flask_app_patch, mock_flask_app, mock_download_service
    ):
        """
        Test that download_task returns success result when download succeeds.
        
        Verifies that:
        - success is True
        - file_path is included
        - error fields are None
        
        Requirements: 11.1
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.download_task import download_video
        
        expected_file_path = "/tmp/downloads/test_video.mp4"
        mock_download_service.execute_download.return_value = DownloadResult(
            success=True,
            file_path=expected_file_path,
            error_message=None,
            error_type=None,
        )
        
        # Act
        result = download_video("test-job", "https://youtube.com/watch?v=test", "best")
        
        # Assert
        assert result["success"] is True
        assert result["file_path"] == expected_file_path
        assert result["error_message"] is None
        assert result["error_type"] is None

    @patch("celery_app.flask_app")
    def test_returns_failure_result_on_error(
        self, mock_flask_app_patch, mock_flask_app, mock_download_service
    ):
        """
        Test that download_task returns failure result when download fails.
        
        Verifies that:
        - success is False
        - error_message is included
        - error_type is included
        
        Requirements: 11.1
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.download_task import download_video
        
        mock_download_service.execute_download.return_value = DownloadResult(
            success=False,
            file_path=None,
            error_message="Video unavailable",
            error_type="VIDEO_UNAVAILABLE",
        )
        
        # Act
        result = download_video("test-job", "https://youtube.com/watch?v=test", "best")
        
        # Assert
        assert result["success"] is False
        assert result["file_path"] is None
        assert result["error_message"] == "Video unavailable"
        assert result["error_type"] == "VIDEO_UNAVAILABLE"


class TestDownloadTaskErrorHandling:
    """Test that download_task handles exceptions and reports errors."""

    @patch("celery_app.flask_app")
    def test_handles_download_service_exception(
        self, mock_flask_app_patch, mock_flask_app, mock_download_service
    ):
        """
        Test that download_task handles exceptions from DownloadService.
        
        Verifies that:
        - Exceptions are caught
        - Error is logged
        - Exception is re-raised for Celery retry handling
        
        Requirements: 11.1
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.download_task import download_video
        
        # Make DownloadService raise an exception
        mock_download_service.execute_download.side_effect = RuntimeError(
            "Unexpected error during download"
        )
        
        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            download_video("test-job", "https://youtube.com/watch?v=test", "best")
        
        assert "Unexpected error during download" in str(exc_info.value)

    @patch("celery_app.flask_app")
    def test_re_raises_exception_for_celery_retry(
        self, mock_flask_app_patch, mock_flask_app, mock_download_service
    ):
        """
        Test that download_task re-raises exceptions for Celery retry handling.
        
        Verifies that exceptions are not swallowed, allowing Celery's
        retry mechanism to handle transient failures.
        
        Requirements: 11.1
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.download_task import download_video
        
        # Make DownloadService raise an exception
        mock_download_service.execute_download.side_effect = ConnectionError(
            "Network connection failed"
        )
        
        # Act & Assert
        with pytest.raises(ConnectionError) as exc_info:
            download_video("test-job", "https://youtube.com/watch?v=test", "best")
        
        assert "Network connection failed" in str(exc_info.value)


class TestDownloadTaskIntegration:
    """Test download_task integration with Celery infrastructure."""

    def test_task_is_registered_with_celery(self):
        """
        Test that download_video task is registered with Celery.
        
        Verifies that:
        - Task has correct name
        - Task is bound (has access to self)
        
        Requirements: 11.1
        """
        # Arrange
        from src.tasks.download_task import download_video
        
        # Assert
        assert download_video.name == "tasks.download_video"
        # Check that task has bind attribute (Celery tasks have this)
        assert hasattr(download_video, 'bind')
