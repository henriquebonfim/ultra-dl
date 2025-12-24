"""
Unit tests for cleanup_task

Tests that the Celery cleanup task calls JobService.cleanup_expired_jobs and
FileManager.cleanup_expired_files, reports cleanup counts, and handles exceptions gracefully.

Requirements: 11.2, 11.3
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta


@pytest.fixture
def mock_job_service():
    """Mock JobService for testing."""
    mock = Mock()
    # Default successful cleanup
    mock.cleanup_expired_jobs.return_value = 5  # 5 jobs cleaned
    return mock


@pytest.fixture
def mock_file_manager():
    """Mock FileManager for testing."""
    mock = Mock()
    # Default successful cleanup
    mock.cleanup_expired_files.return_value = 3  # 3 files cleaned
    return mock


@pytest.fixture
def mock_container(mock_job_service, mock_file_manager):
    """Mock DependencyContainer."""
    mock = MagicMock()
    
    # Configure container to return appropriate service based on type
    def resolve_side_effect(service_type):
        from src.application.job_service import JobService
        from src.domain.file_storage.services import FileManager
        
        if service_type == JobService:
            return mock_job_service
        elif service_type == FileManager:
            return mock_file_manager
        else:
            raise ValueError(f"Unknown service type: {service_type}")
    
    mock.resolve.side_effect = resolve_side_effect
    return mock


@pytest.fixture
def mock_flask_app(mock_container):
    """Mock Flask app with DependencyContainer."""
    mock_app = MagicMock()
    mock_app.container = mock_container
    return mock_app


class TestCleanupTaskServiceResolution:
    """Test that cleanup_task uses DependencyContainer for service resolution."""

    @patch("celery_app.flask_app")
    def test_resolves_job_service_from_container(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service
    ):
        """
        Test that cleanup_task resolves JobService from DependencyContainer.
        
        Verifies that:
        - Task accesses flask_app.container
        - container.resolve() is called with JobService
        - Task never instantiates services directly
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        from src.application.job_service import JobService
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        # Verify container.resolve was called with JobService
        resolve_calls = mock_flask_app.container.resolve.call_args_list
        assert any(call[0][0] == JobService for call in resolve_calls)

    @patch("celery_app.flask_app")
    def test_resolves_file_manager_from_container(
        self, mock_flask_app_patch, mock_flask_app, mock_file_manager
    ):
        """
        Test that cleanup_task resolves FileManager from DependencyContainer.
        
        Verifies that:
        - Task accesses flask_app.container
        - container.resolve() is called with FileManager
        - Task never instantiates services directly
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        from src.domain.file_storage.services import FileManager
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        # Verify container.resolve was called with FileManager
        resolve_calls = mock_flask_app.container.resolve.call_args_list
        assert any(call[0][0] == FileManager for call in resolve_calls)


class TestCleanupTaskJobCleaning:
    """Test that cleanup_task calls JobService.cleanup_expired_jobs."""

    @patch("celery_app.flask_app")
    def test_calls_cleanup_expired_jobs(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service
    ):
        """
        Test that cleanup_task calls JobService.cleanup_expired_jobs.
        
        Verifies that:
        - cleanup_expired_jobs is called
        - Correct expiration_hours parameter is passed (1 hour)
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        mock_job_service.cleanup_expired_jobs.assert_called_once_with(expiration_hours=1)

    @patch("celery_app.flask_app")
    def test_reports_jobs_cleaned_count(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service
    ):
        """
        Test that cleanup_task reports the count of jobs cleaned.
        
        Verifies that:
        - Return value includes expired_jobs_removed count
        - Count matches JobService return value
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        mock_job_service.cleanup_expired_jobs.return_value = 12
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        assert result["expired_jobs_removed"] == 12


class TestCleanupTaskFileCleaning:
    """Test that cleanup_task calls FileManager.cleanup_expired_files."""

    @patch("celery_app.flask_app")
    def test_calls_cleanup_expired_files(
        self, mock_flask_app_patch, mock_flask_app, mock_file_manager
    ):
        """
        Test that cleanup_task calls FileManager.cleanup_expired_files.
        
        Verifies that:
        - cleanup_expired_files is called
        - No parameters are required
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        mock_file_manager.cleanup_expired_files.assert_called_once()

    @patch("celery_app.flask_app")
    def test_reports_files_cleaned_count(
        self, mock_flask_app_patch, mock_flask_app, mock_file_manager
    ):
        """
        Test that cleanup_task reports the count of files cleaned.
        
        Verifies that:
        - Return value includes expired_files_cleaned count
        - Count matches FileManager return value
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        mock_file_manager.cleanup_expired_files.return_value = 8
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        assert result["expired_files_cleaned"] == 8


class TestCleanupTaskErrorHandling:
    """Test that cleanup_task handles exceptions gracefully."""

    @patch("celery_app.flask_app")
    def test_handles_job_cleanup_exception_gracefully(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service, mock_file_manager
    ):
        """
        Test that cleanup_task handles JobService exceptions gracefully.
        
        Verifies that:
        - Exception is caught and logged
        - Task continues to clean files
        - Error is included in result
        - Task does not crash
        
        Requirements: 11.3
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        # Make JobService raise an exception
        error_message = "Database connection failed"
        mock_job_service.cleanup_expired_jobs.side_effect = RuntimeError(error_message)
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        # Task should not crash
        assert result is not None
        
        # Error should be in result
        assert len(result["errors"]) > 0
        assert any(error_message in error for error in result["errors"])
        
        # Job cleanup count should be 0
        assert result["expired_jobs_removed"] == 0
        
        # File cleanup should still be attempted
        mock_file_manager.cleanup_expired_files.assert_called_once()

    @patch("celery_app.flask_app")
    def test_handles_file_cleanup_exception_gracefully(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service, mock_file_manager
    ):
        """
        Test that cleanup_task handles FileManager exceptions gracefully.
        
        Verifies that:
        - Exception is caught and logged
        - Task continues to clean orphaned files
        - Error is included in result
        - Task does not crash
        
        Requirements: 11.3
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        # Make FileManager raise an exception
        error_message = "Storage service unavailable"
        mock_file_manager.cleanup_expired_files.side_effect = RuntimeError(error_message)
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        # Task should not crash
        assert result is not None
        
        # Error should be in result
        assert len(result["errors"]) > 0
        assert any(error_message in error for error in result["errors"])
        
        # File cleanup count should be 0
        assert result["expired_files_cleaned"] == 0
        
        # Job cleanup should have succeeded
        assert result["expired_jobs_removed"] > 0

    @patch("celery_app.flask_app")
    def test_handles_multiple_exceptions_gracefully(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service, mock_file_manager
    ):
        """
        Test that cleanup_task handles multiple exceptions gracefully.
        
        Verifies that:
        - Multiple exceptions are caught
        - All errors are included in result
        - Task completes and returns result
        
        Requirements: 11.3
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        # Make both services raise exceptions
        mock_job_service.cleanup_expired_jobs.side_effect = RuntimeError("Job error")
        mock_file_manager.cleanup_expired_files.side_effect = RuntimeError("File error")
        
        # Act
        result = cleanup_expired_jobs()
        
        # Assert
        # Task should not crash
        assert result is not None
        
        # Both errors should be in result
        assert len(result["errors"]) >= 2
        assert any("Job error" in error for error in result["errors"])
        assert any("File error" in error for error in result["errors"])


class TestCleanupTaskReporting:
    """Test that cleanup_task reports cleanup statistics correctly."""

    @patch("celery_app.flask_app")
    def test_returns_complete_cleanup_stats(
        self, mock_flask_app_patch, mock_flask_app, mock_job_service, mock_file_manager
    ):
        """
        Test that cleanup_task returns complete cleanup statistics.
        
        Verifies that result includes:
        - expired_jobs_removed
        - expired_files_cleaned
        - orphaned_files_cleaned
        - errors list
        
        Requirements: 11.2
        """
        # Arrange
        mock_flask_app_patch.container = mock_flask_app.container
        
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        mock_job_service.cleanup_expired_jobs.return_value = 7
        mock_file_manager.cleanup_expired_files.return_value = 4
        
        # Act
        with patch("src.tasks.cleanup_task._cleanup_orphaned_files", return_value=2):
            result = cleanup_expired_jobs()
        
        # Assert
        assert "expired_jobs_removed" in result
        assert "expired_files_cleaned" in result
        assert "orphaned_files_cleaned" in result
        assert "errors" in result
        
        assert result["expired_jobs_removed"] == 7
        assert result["expired_files_cleaned"] == 4
        assert result["orphaned_files_cleaned"] == 2
        assert isinstance(result["errors"], list)


class TestCleanupTaskIntegration:
    """Test cleanup_task integration with Celery infrastructure."""

    def test_task_is_registered_with_celery(self):
        """
        Test that cleanup_expired_jobs task is registered with Celery.
        
        Verifies that:
        - Task has correct name
        - Task is bound (has access to self)
        
        Requirements: 11.2
        """
        # Arrange
        from src.tasks.cleanup_task import cleanup_expired_jobs
        
        # Assert
        assert cleanup_expired_jobs.name == "tasks.cleanup_expired_jobs"
        # Check that task has bind attribute (Celery tasks have this)
        assert hasattr(cleanup_expired_jobs, 'bind')
