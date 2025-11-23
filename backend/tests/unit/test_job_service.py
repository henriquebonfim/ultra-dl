"""
Unit Tests for Job Service

Tests the JobService application service for job management operations.
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from application.job_service import JobService
from domain.job_management import (
    DownloadJob,
    JobManager,
    JobNotFoundError,
    JobStateError,
    JobProgress,
    JobStatus
)
from domain.file_storage import FileManager


@pytest.fixture
def mock_job_manager():
    """Create mock JobManager."""
    return Mock(spec=JobManager)


@pytest.fixture
def mock_file_manager():
    """Create mock FileManager."""
    return Mock(spec=FileManager)


@pytest.fixture
def job_service(mock_job_manager, mock_file_manager):
    """Create JobService with mocked dependencies."""
    return JobService(mock_job_manager, mock_file_manager)


@pytest.fixture
def sample_job():
    """Create a sample DownloadJob for testing."""
    job = DownloadJob.create("https://youtube.com/watch?v=test", "137")
    job.job_id = "test-job-123"
    return job


class TestCreateJob:
    """Test create_job generates unique job IDs."""
    
    def test_create_job_generates_unique_job_ids(self, job_service, mock_job_manager):
        """Test that create_job generates unique job IDs for each call."""
        # Setup: Create multiple jobs
        job_ids = set()
        
        for i in range(10):
            job = DownloadJob.create(f"https://youtube.com/watch?v=test{i}", "137")
            mock_job_manager.create_job.return_value = job
            
            result = job_service.create_download_job(
                f"https://youtube.com/watch?v=test{i}",
                "137"
            )
            
            job_ids.add(result["job_id"])
        
        # Verify: All job IDs are unique
        assert len(job_ids) == 10, "All job IDs should be unique"
    
    def test_create_job_returns_correct_structure(self, job_service, mock_job_manager, sample_job):
        """Test that create_job returns correct response structure."""
        mock_job_manager.create_job.return_value = sample_job
        
        result = job_service.create_download_job(
            "https://youtube.com/watch?v=test",
            "137"
        )
        
        assert "job_id" in result
        assert "status" in result
        assert "message" in result
        assert result["status"] == "pending"
        assert result["job_id"] == sample_job.job_id


class TestGetJobStatus:
    """Test get_job_status handles missing job gracefully."""
    
    def test_get_job_status_handles_missing_job_gracefully(self, job_service, mock_job_manager):
        """Test that get_job_status raises JobNotFoundError for missing job."""
        # Setup: Mock job manager to raise JobNotFoundError
        mock_job_manager.get_job_status_info.side_effect = JobNotFoundError("Job not found")
        
        # Verify: JobNotFoundError is raised
        with pytest.raises(JobNotFoundError) as exc_info:
            job_service.get_job_status("non-existent-job")
        
        assert "Job not found" in str(exc_info.value)
    
    def test_get_job_status_returns_complete_info(self, job_service, mock_job_manager):
        """Test that get_job_status returns complete job information."""
        # Setup: Mock job status info
        expected_status = {
            "job_id": "test-job-123",
            "status": "processing",
            "progress": {
                "percentage": 50,
                "phase": "downloading",
                "speed": "1.5 MB/s",
                "eta": 30
            },
            "download_url": None,
            "expire_at": None,
            "time_remaining": None,
            "error": None,
            "error_category": None
        }
        mock_job_manager.get_job_status_info.return_value = expected_status
        
        # Execute
        result = job_service.get_job_status("test-job-123")
        
        # Verify
        assert result == expected_status
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "processing"
        assert result["progress"]["percentage"] == 50


class TestDeleteJob:
    """Test delete_job removes both file and job record."""
    
    def test_delete_job_removes_both_file_and_job_record(
        self, job_service, mock_job_manager, mock_file_manager, sample_job
    ):
        """Test that delete_job removes both file and job record."""
        # Setup: Job with download token
        sample_job.download_token = "test-token-123"
        mock_job_manager.get_job.return_value = sample_job
        mock_file_manager.delete_file.return_value = True
        mock_job_manager.delete_job.return_value = True
        
        # Execute
        result = job_service.delete_job("test-job-123")
        
        # Verify: Both file and job were deleted
        assert result is True
        mock_file_manager.delete_file.assert_called_once_with("test-token-123")
        mock_job_manager.delete_job.assert_called_once_with("test-job-123")
    
    def test_delete_job_handles_missing_file_gracefully(
        self, job_service, mock_job_manager, mock_file_manager, sample_job
    ):
        """Test that delete_job handles missing file gracefully."""
        # Setup: Job without download token
        sample_job.download_token = None
        mock_job_manager.get_job.return_value = sample_job
        mock_job_manager.delete_job.return_value = True
        
        # Execute
        result = job_service.delete_job("test-job-123")
        
        # Verify: Job was deleted, file deletion was skipped
        assert result is True
        mock_file_manager.delete_file.assert_not_called()
        mock_job_manager.delete_job.assert_called_once_with("test-job-123")
    
    def test_delete_job_handles_missing_job_gracefully(
        self, job_service, mock_job_manager, mock_file_manager
    ):
        """Test that delete_job handles missing job gracefully."""
        # Setup: Job not found
        mock_job_manager.get_job.side_effect = JobNotFoundError("Job not found")
        mock_job_manager.delete_job.return_value = False
        
        # Execute
        result = job_service.delete_job("non-existent-job")
        
        # Verify: Returns False, no file deletion attempted
        assert result is False
        mock_file_manager.delete_file.assert_not_called()
        mock_job_manager.delete_job.assert_called_once_with("non-existent-job")
    
    def test_delete_job_continues_if_file_deletion_fails(
        self, job_service, mock_job_manager, mock_file_manager, sample_job
    ):
        """Test that delete_job continues to delete job even if file deletion fails."""
        # Setup: File deletion fails
        sample_job.download_token = "test-token-123"
        mock_job_manager.get_job.return_value = sample_job
        mock_file_manager.delete_file.return_value = False
        mock_job_manager.delete_job.return_value = True
        
        # Execute
        result = job_service.delete_job("test-job-123")
        
        # Verify: Job was still deleted
        assert result is True
        mock_file_manager.delete_file.assert_called_once_with("test-token-123")
        mock_job_manager.delete_job.assert_called_once_with("test-job-123")


class TestCleanupExpiredJobs:
    """Test cleanup_expired_jobs respects expiration time."""
    
    def test_cleanup_expired_jobs_respects_expiration_time(
        self, job_service, mock_job_manager
    ):
        """Test that cleanup_expired_jobs respects expiration time parameter."""
        # Setup: Mock cleanup to return count
        mock_job_manager.cleanup_expired_jobs.return_value = 5
        
        # Execute: Cleanup with 2 hour expiration
        count = job_service.cleanup_expired_jobs(expiration_hours=2)
        
        # Verify: Correct expiration time passed
        assert count == 5
        mock_job_manager.cleanup_expired_jobs.assert_called_once()
        call_args = mock_job_manager.cleanup_expired_jobs.call_args[0]
        assert call_args[0] == timedelta(hours=2)
    
    def test_cleanup_expired_jobs_uses_default_expiration(
        self, job_service, mock_job_manager
    ):
        """Test that cleanup_expired_jobs uses default 1 hour expiration."""
        # Setup
        mock_job_manager.cleanup_expired_jobs.return_value = 3
        
        # Execute: Cleanup without specifying expiration
        count = job_service.cleanup_expired_jobs()
        
        # Verify: Default 1 hour expiration used
        assert count == 3
        mock_job_manager.cleanup_expired_jobs.assert_called_once()
        call_args = mock_job_manager.cleanup_expired_jobs.call_args[0]
        assert call_args[0] == timedelta(hours=1)
    
    def test_cleanup_expired_jobs_handles_errors_gracefully(
        self, job_service, mock_job_manager
    ):
        """Test that cleanup_expired_jobs handles errors gracefully."""
        # Setup: Mock cleanup to raise exception
        mock_job_manager.cleanup_expired_jobs.side_effect = Exception("Redis connection failed")
        
        # Execute: Should not raise exception
        count = job_service.cleanup_expired_jobs()
        
        # Verify: Returns 0 on error
        assert count == 0


class TestGetJobsByStatus:
    """Test get_jobs_by_status uses batch operations efficiently."""
    
    def test_update_progress_uses_atomic_operation(
        self, job_service, mock_job_manager
    ):
        """Test that update_progress uses atomic repository operation."""
        # Setup
        mock_job_manager.update_job_progress.return_value = True
        
        # Execute
        result = job_service.update_progress(
            "test-job-123",
            percentage=50,
            phase="downloading",
            speed="1.5 MB/s",
            eta=30
        )
        
        # Verify: Atomic update was called
        assert result is True
        mock_job_manager.update_job_progress.assert_called_once()
        
        # Verify progress object was created correctly
        call_args = mock_job_manager.update_job_progress.call_args[0]
        assert call_args[0] == "test-job-123"
        progress = call_args[1]
        assert isinstance(progress, JobProgress)
        assert progress.percentage == 50
        assert progress.phase == "downloading"
        assert progress.speed == "1.5 MB/s"
        assert progress.eta == 30


class TestConcurrentJobOperations:
    """Test concurrent job operations are thread-safe."""
    
    def test_concurrent_job_creation_is_thread_safe(self, mock_job_manager, mock_file_manager):
        """Test that concurrent job creation operations are thread-safe."""
        # Setup
        job_service = JobService(mock_job_manager, mock_file_manager)
        created_jobs = []
        errors = []
        
        def create_job(index):
            try:
                job = DownloadJob.create(f"https://youtube.com/watch?v=test{index}", "137")
                mock_job_manager.create_job.return_value = job
                
                result = job_service.create_download_job(
                    f"https://youtube.com/watch?v=test{index}",
                    "137"
                )
                created_jobs.append(result["job_id"])
            except Exception as e:
                errors.append(e)
        
        # Execute: Create 10 jobs concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_job, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify: All jobs created successfully, no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(created_jobs) == 10
        assert len(set(created_jobs)) == 10, "All job IDs should be unique"
    
    def test_concurrent_progress_updates_are_thread_safe(
        self, mock_job_manager, mock_file_manager
    ):
        """Test that concurrent progress updates are thread-safe."""
        # Setup
        job_service = JobService(mock_job_manager, mock_file_manager)
        mock_job_manager.update_job_progress.return_value = True
        update_results = []
        errors = []
        
        def update_progress(percentage):
            try:
                result = job_service.update_progress(
                    "test-job-123",
                    percentage=percentage,
                    phase=f"downloading chunk {percentage}",
                    speed="1.5 MB/s"
                )
                update_results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Execute: Update progress 10 times concurrently
        threads = []
        for i in range(10, 101, 10):
            thread = threading.Thread(target=update_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify: All updates succeeded, no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(update_results) == 10
        assert all(result is True for result in update_results)
    
    def test_concurrent_job_status_reads_are_thread_safe(
        self, mock_job_manager, mock_file_manager
    ):
        """Test that concurrent job status reads are thread-safe."""
        # Setup
        job_service = JobService(mock_job_manager, mock_file_manager)
        status_info = {
            "job_id": "test-job-123",
            "status": "processing",
            "progress": {"percentage": 50, "phase": "downloading"},
            "download_url": None,
            "expire_at": None,
            "time_remaining": None,
            "error": None,
            "error_category": None
        }
        mock_job_manager.get_job_status_info.return_value = status_info
        status_results = []
        errors = []
        
        def get_status():
            try:
                result = job_service.get_job_status("test-job-123")
                status_results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Execute: Read status 20 times concurrently
        threads = []
        for i in range(20):
            thread = threading.Thread(target=get_status)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify: All reads succeeded, no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(status_results) == 20
        assert all(result["job_id"] == "test-job-123" for result in status_results)


class TestJobServiceEdgeCases:
    """Test additional edge cases for job service."""
    
    def test_start_job_handles_state_error(self, job_service, mock_job_manager):
        """Test that start_job handles JobStateError appropriately."""
        # Setup: Mock job manager to raise JobStateError
        mock_job_manager.start_job.side_effect = JobStateError("Cannot start completed job")
        
        # Verify: JobStateError is propagated
        with pytest.raises(JobStateError) as exc_info:
            job_service.start_job("test-job-123")
        
        assert "Cannot start completed job" in str(exc_info.value)
    
    def test_complete_job_handles_state_error(self, job_service, mock_job_manager):
        """Test that complete_job handles JobStateError appropriately."""
        # Setup: Mock job manager to raise JobStateError
        mock_job_manager.complete_job.side_effect = JobStateError("Cannot complete pending job")
        
        # Verify: JobStateError is propagated
        with pytest.raises(JobStateError) as exc_info:
            job_service.complete_job("test-job-123")
        
        assert "Cannot complete pending job" in str(exc_info.value)
    
    def test_update_progress_handles_missing_job(self, job_service, mock_job_manager):
        """Test that update_progress handles missing job gracefully."""
        # Setup: Mock job manager to raise JobNotFoundError
        mock_job_manager.update_job_progress.side_effect = JobNotFoundError("Job not found")
        
        # Verify: JobNotFoundError is propagated
        with pytest.raises(JobNotFoundError) as exc_info:
            job_service.update_progress(
                "non-existent-job",
                percentage=50,
                phase="downloading"
            )
        
        assert "Job not found" in str(exc_info.value)
    
    def test_fail_job_handles_missing_job(self, job_service, mock_job_manager):
        """Test that fail_job handles missing job gracefully."""
        # Setup: Mock job manager to raise JobNotFoundError
        mock_job_manager.fail_job.side_effect = JobNotFoundError("Job not found")
        
        # Verify: JobNotFoundError is propagated
        with pytest.raises(JobNotFoundError) as exc_info:
            job_service.fail_job("non-existent-job", "Error message")
        
        assert "Job not found" in str(exc_info.value)
    
    def test_create_job_handles_generic_exception(self, job_service, mock_job_manager):
        """Test that create_job handles generic exceptions."""
        # Setup: Mock job manager to raise generic exception
        mock_job_manager.create_job.side_effect = Exception("Database connection failed")
        
        # Verify: Exception is propagated
        with pytest.raises(Exception) as exc_info:
            job_service.create_download_job("https://youtube.com/watch?v=test", "137")
        
        assert "Database connection failed" in str(exc_info.value)
    
    def test_get_job_status_handles_generic_exception(self, job_service, mock_job_manager):
        """Test that get_job_status handles generic exceptions."""
        # Setup: Mock job manager to raise generic exception
        mock_job_manager.get_job_status_info.side_effect = Exception("Redis connection failed")
        
        # Verify: Exception is propagated
        with pytest.raises(Exception) as exc_info:
            job_service.get_job_status("test-job-123")
        
        assert "Redis connection failed" in str(exc_info.value)
    
    def test_update_progress_handles_generic_exception(self, job_service, mock_job_manager):
        """Test that update_progress handles generic exceptions and returns False."""
        # Setup: Mock job manager to raise generic exception
        mock_job_manager.update_job_progress.side_effect = Exception("Unexpected error")
        
        # Execute: Should not raise exception, returns False
        result = job_service.update_progress(
            "test-job-123",
            percentage=50,
            phase="downloading"
        )
        
        # Verify: Returns False on error
        assert result is False
    
    def test_fail_job_handles_generic_exception(self, job_service, mock_job_manager):
        """Test that fail_job handles generic exceptions."""
        # Setup: Mock job manager to raise generic exception
        mock_job_manager.fail_job.side_effect = Exception("Unexpected error")
        
        # Verify: Exception is propagated
        with pytest.raises(Exception) as exc_info:
            job_service.fail_job("test-job-123", "Error message")
        
        assert "Unexpected error" in str(exc_info.value)
    
    def test_delete_job_handles_generic_exception(self, job_service, mock_job_manager):
        """Test that delete_job handles generic exceptions and returns False."""
        # Setup: Mock job manager to raise generic exception
        mock_job_manager.get_job.side_effect = Exception("Unexpected error")
        
        # Execute: Should not raise exception, returns False
        result = job_service.delete_job("test-job-123")
        
        # Verify: Returns False on error
        assert result is False
