"""
Unit tests for JobService

Tests job creation and retrieval, cleanup_expired_jobs calls JobManager correctly,
and error handling for job operations.

Requirements: 2.1, 2.2
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.application.job_service import JobService
from src.domain.job_management.services import JobManager
from src.domain.job_management.entities import DownloadJob
from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.job_management import JobNotFoundError, JobStateError
from src.domain.file_storage.services import FileManager

from tests.fixtures.domain_fixtures import create_download_job


@pytest.fixture
def mock_job_manager():
    """Mock JobManager for testing."""
    mock = Mock(spec=JobManager)
    mock.create_job.return_value = create_download_job()
    mock.get_job.return_value = create_download_job()
    mock.get_job_status_info.return_value = {
        "job_id": "test-123",
        "status": "pending",
        "progress": {"percentage": 0, "phase": "initial"},
    }
    mock.start_job.return_value = create_download_job(status=JobStatus.PROCESSING)
    mock.update_job_progress.return_value = True
    mock.complete_job.return_value = create_download_job(status=JobStatus.COMPLETED)
    mock.fail_job.return_value = create_download_job(status=JobStatus.FAILED)
    mock.delete_job.return_value = True
    mock.cleanup_expired_jobs.return_value = 5
    return mock


@pytest.fixture
def mock_file_manager():
    """Mock FileManager for testing."""
    mock = Mock(spec=FileManager)
    mock.delete_file.return_value = True
    return mock


@pytest.fixture
def job_service(mock_job_manager, mock_file_manager):
    """Create JobService with mocked dependencies."""
    return JobService(job_manager=mock_job_manager, file_manager=mock_file_manager)


class TestJobServiceCreation:
    """Test job creation operations."""

    def test_create_download_job_success(self, job_service, mock_job_manager):
        """
        Test successful job creation.
        
        Verifies that:
        - JobManager.create_job is called with correct parameters
        - Returns dictionary with job_id, status, and message
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"
        
        # Act
        result = job_service.create_download_job(url, format_id)
        
        # Assert
        mock_job_manager.create_job.assert_called_once_with(url, format_id)
        assert "job_id" in result
        assert "status" in result
        assert "message" in result
        assert result["status"] == "pending"

    def test_create_download_job_propagates_exception(self, job_service, mock_job_manager):
        """
        Test that exceptions from JobManager are propagated.
        
        Verifies that exceptions raised by JobManager.create_job
        are not caught and suppressed.
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"
        mock_job_manager.create_job.side_effect = Exception("Creation failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Creation failed"):
            job_service.create_download_job(url, format_id)


class TestJobServiceRetrieval:
    """Test job retrieval operations."""

    def test_get_job_status_success(self, job_service, mock_job_manager):
        """
        Test successful job status retrieval.
        
        Verifies that JobManager.get_job_status_info is called
        and returns status information.
        """
        # Arrange
        job_id = "test-job-123"
        
        # Act
        result = job_service.get_job_status(job_id)
        
        # Assert
        mock_job_manager.get_job_status_info.assert_called_once_with(job_id)
        assert "job_id" in result
        assert "status" in result

    def test_get_job_status_not_found(self, job_service, mock_job_manager):
        """
        Test job status retrieval when job doesn't exist.
        
        Verifies that JobNotFoundError is raised when job
        doesn't exist.
        """
        # Arrange
        job_id = "nonexistent-job"
        mock_job_manager.get_job_status_info.side_effect = JobNotFoundError(
            f"Job {job_id} not found"
        )
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            job_service.get_job_status(job_id)

    def test_start_job_success(self, job_service, mock_job_manager):
        """
        Test successful job start.
        
        Verifies that JobManager.start_job is called and
        returns updated job.
        """
        # Arrange
        job_id = "test-job-123"
        
        # Act
        result = job_service.start_job(job_id)
        
        # Assert
        mock_job_manager.start_job.assert_called_once_with(job_id)
        assert result.status == JobStatus.PROCESSING

    def test_start_job_invalid_state(self, job_service, mock_job_manager):
        """
        Test starting job in invalid state.
        
        Verifies that JobStateError is raised when job
        cannot be started.
        """
        # Arrange
        job_id = "test-job-123"
        mock_job_manager.start_job.side_effect = JobStateError(
            "Job cannot be started from current state"
        )
        
        # Act & Assert
        with pytest.raises(JobStateError):
            job_service.start_job(job_id)


class TestJobServiceProgressUpdates:
    """Test job progress update operations."""

    def test_update_progress_success(self, job_service, mock_job_manager):
        """
        Test successful progress update.
        
        Verifies that JobManager.update_job_progress is called
        with correct JobProgress object.
        """
        # Arrange
        job_id = "test-job-123"
        percentage = 50
        phase = "downloading"
        speed = "1.5 MB/s"
        eta = 30
        
        # Act
        result = job_service.update_progress(job_id, percentage, phase, speed, eta)
        
        # Assert
        assert result is True
        mock_job_manager.update_job_progress.assert_called_once()
        # Verify JobProgress was created correctly
        call_args = mock_job_manager.update_job_progress.call_args
        assert call_args[0][0] == job_id
        progress = call_args[0][1]
        assert progress.percentage == percentage
        assert progress.phase == phase
        assert progress.speed == speed
        assert progress.eta == eta

    def test_update_progress_job_not_found(self, job_service, mock_job_manager):
        """
        Test progress update when job doesn't exist.
        
        Verifies that JobNotFoundError is raised.
        """
        # Arrange
        job_id = "nonexistent-job"
        mock_job_manager.update_job_progress.side_effect = JobNotFoundError(
            f"Job {job_id} not found"
        )
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            job_service.update_progress(job_id, 50, "downloading")

    def test_update_progress_handles_generic_exception(self, job_service, mock_job_manager):
        """
        Test that generic exceptions during progress update are handled.
        
        Verifies that exceptions are caught and False is returned.
        """
        # Arrange
        job_id = "test-job-123"
        mock_job_manager.update_job_progress.side_effect = Exception("Update failed")
        
        # Act
        result = job_service.update_progress(job_id, 50, "downloading")
        
        # Assert
        assert result is False


class TestJobServiceCompletion:
    """Test job completion operations."""

    def test_complete_job_success(self, job_service, mock_job_manager):
        """
        Test successful job completion.
        
        Verifies that JobManager.complete_job is called with
        correct parameters.
        """
        # Arrange
        job_id = "test-job-123"
        download_url = "https://example.com/download/test"
        download_token = "test-token-123"
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Act
        result = job_service.complete_job(job_id, download_url, download_token, expire_at)
        
        # Assert
        mock_job_manager.complete_job.assert_called_once_with(
            job_id, download_url, download_token, expire_at
        )
        assert result.status == JobStatus.COMPLETED

    def test_complete_job_not_found(self, job_service, mock_job_manager):
        """
        Test completing job that doesn't exist.
        
        Verifies that JobNotFoundError is raised.
        """
        # Arrange
        job_id = "nonexistent-job"
        mock_job_manager.complete_job.side_effect = JobNotFoundError(
            f"Job {job_id} not found"
        )
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            job_service.complete_job(job_id)

    def test_fail_job_success(self, job_service, mock_job_manager):
        """
        Test successful job failure marking.
        
        Verifies that JobManager.fail_job is called with
        error message.
        """
        # Arrange
        job_id = "test-job-123"
        error_message = "Download failed due to network error"
        
        # Act
        result = job_service.fail_job(job_id, error_message)
        
        # Assert
        mock_job_manager.fail_job.assert_called_once_with(job_id, error_message)
        assert result.status == JobStatus.FAILED

    def test_fail_job_not_found(self, job_service, mock_job_manager):
        """
        Test failing job that doesn't exist.
        
        Verifies that JobNotFoundError is raised.
        """
        # Arrange
        job_id = "nonexistent-job"
        mock_job_manager.fail_job.side_effect = JobNotFoundError(
            f"Job {job_id} not found"
        )
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            job_service.fail_job(job_id, "Error message")


class TestJobServiceCleanup:
    """Test job cleanup operations."""

    def test_cleanup_expired_jobs_calls_job_manager(self, job_service, mock_job_manager, mock_file_manager):
        """
        Test that cleanup_expired_jobs calls JobManager correctly.
        
        Verifies that:
        - JobManager.cleanup_expired_jobs is called with correct expiration time
        - FileManager is passed to JobManager for file deletion coordination
        - Returns count of cleaned up jobs
        """
        # Arrange
        expiration_hours = 2
        
        # Act
        result = job_service.cleanup_expired_jobs(expiration_hours)
        
        # Assert
        mock_job_manager.cleanup_expired_jobs.assert_called_once()
        call_args = mock_job_manager.cleanup_expired_jobs.call_args
        # Verify timedelta was passed
        assert isinstance(call_args[0][0], timedelta)
        assert call_args[0][0] == timedelta(hours=expiration_hours)
        # Verify file_manager was passed
        assert call_args[1]["file_manager"] == mock_file_manager
        assert result == 5

    def test_cleanup_expired_jobs_default_expiration(self, job_service, mock_job_manager):
        """
        Test cleanup with default expiration time.
        
        Verifies that default expiration of 1 hour is used.
        """
        # Act
        result = job_service.cleanup_expired_jobs()
        
        # Assert
        mock_job_manager.cleanup_expired_jobs.assert_called_once()
        call_args = mock_job_manager.cleanup_expired_jobs.call_args
        assert call_args[0][0] == timedelta(hours=1)

    def test_cleanup_expired_jobs_handles_exception(self, job_service, mock_job_manager):
        """
        Test that cleanup handles exceptions gracefully.
        
        Verifies that exceptions are caught and 0 is returned.
        """
        # Arrange
        mock_job_manager.cleanup_expired_jobs.side_effect = Exception("Cleanup failed")
        
        # Act
        result = job_service.cleanup_expired_jobs()
        
        # Assert
        assert result == 0

    def test_delete_job_success(self, job_service, mock_job_manager, mock_file_manager):
        """
        Test successful job deletion.
        
        Verifies that:
        - Job is retrieved to get download_token
        - File is deleted using FileManager
        - Job is deleted using JobManager
        """
        # Arrange
        job_id = "test-job-123"
        job = create_download_job(job_id=job_id)
        job.download_token = "test-token-123"
        mock_job_manager.get_job.return_value = job
        
        # Act
        result = job_service.delete_job(job_id)
        
        # Assert
        assert result is True
        mock_job_manager.get_job.assert_called_once_with(job_id)
        mock_file_manager.delete_file.assert_called_once_with("test-token-123")
        mock_job_manager.delete_job.assert_called_once_with(job_id)

    def test_delete_job_without_file(self, job_service, mock_job_manager, mock_file_manager):
        """
        Test deleting job without associated file.
        
        Verifies that job is deleted even if no file exists.
        """
        # Arrange
        job_id = "test-job-123"
        job = create_download_job(job_id=job_id)
        job.download_token = None  # No file
        mock_job_manager.get_job.return_value = job
        
        # Act
        result = job_service.delete_job(job_id)
        
        # Assert
        assert result is True
        mock_file_manager.delete_file.assert_not_called()
        mock_job_manager.delete_job.assert_called_once_with(job_id)

    def test_delete_job_not_found(self, job_service, mock_job_manager, mock_file_manager):
        """
        Test deleting job that doesn't exist.
        
        Verifies that deletion continues even if job not found.
        """
        # Arrange
        job_id = "nonexistent-job"
        mock_job_manager.get_job.side_effect = JobNotFoundError(f"Job {job_id} not found")
        
        # Act
        result = job_service.delete_job(job_id)
        
        # Assert
        # Should still attempt to delete the job record
        mock_job_manager.delete_job.assert_called_once_with(job_id)

    def test_delete_job_handles_exception(self, job_service, mock_job_manager):
        """
        Test that delete_job handles exceptions gracefully.
        
        Verifies that exceptions are caught and False is returned.
        """
        # Arrange
        job_id = "test-job-123"
        mock_job_manager.get_job.side_effect = Exception("Unexpected error")
        
        # Act
        result = job_service.delete_job(job_id)
        
        # Assert
        assert result is False


class TestJobServiceErrorHandling:
    """Test error handling across JobService operations."""

    def test_handles_job_not_found_error(self, job_service, mock_job_manager):
        """
        Test that JobNotFoundError is properly propagated.
        
        Verifies that domain exceptions are not wrapped or suppressed.
        """
        # Arrange
        job_id = "nonexistent-job"
        mock_job_manager.get_job_status_info.side_effect = JobNotFoundError(
            f"Job {job_id} not found"
        )
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            job_service.get_job_status(job_id)

    def test_handles_job_state_error(self, job_service, mock_job_manager):
        """
        Test that JobStateError is properly propagated.
        
        Verifies that state transition errors are not suppressed.
        """
        # Arrange
        job_id = "test-job-123"
        mock_job_manager.complete_job.side_effect = JobStateError(
            "Cannot complete job in current state"
        )
        
        # Act & Assert
        with pytest.raises(JobStateError):
            job_service.complete_job(job_id)
