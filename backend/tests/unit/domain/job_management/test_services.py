"""
Unit tests for JobManager service.

Tests verify JobManager business logic with mocked repository interfaces:
- Job creation and retrieval
- State transitions
- Progress updates
- Error handling
- Cleanup with archival flow

Requirements: 1.3, 1.4
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from src.domain.job_management.services import JobManager, JobNotFoundError, JobStateError
from src.domain.job_management.entities import DownloadJob, JobArchive
from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.video_processing.value_objects import FormatId
from src.domain.file_storage.value_objects import DownloadToken


class TestJobManagerService:
    """Test JobManager service business logic."""
    
    def test_create_job_creates_and_saves_job(self):
        """
        Test that create_job() creates a new job and saves it to repository.
        
        Verifies:
        - Job is created with correct URL and format
        - Job is saved to repository
        - Created job is returned
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.save.return_value = True
        manager = JobManager(mock_repo)
        
        url = "https://youtube.com/watch?v=test"
        format_id = "best"
        
        # Act
        job = manager.create_job(url, format_id)
        
        # Assert
        assert job is not None
        assert job.url == url
        assert str(job.format_id) == format_id
        assert job.status == JobStatus.PENDING
        mock_repo.save.assert_called_once()
        saved_job = mock_repo.save.call_args[0][0]
        assert saved_job.job_id == job.job_id
    
    def test_create_job_raises_exception_when_save_fails(self):
        """
        Test that create_job() raises exception when repository save fails.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.save.return_value = False
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            manager.create_job("https://youtube.com/watch?v=test", "best")
        assert "Failed to save job" in str(exc_info.value)
    
    def test_get_job_retrieves_existing_job(self):
        """
        Test that get_job() retrieves an existing job from repository.
        
        Verifies:
        - Repository get() is called with correct job_id
        - Job is returned
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act
        retrieved_job = manager.get_job(job.job_id)
        
        # Assert
        assert retrieved_job == job
        mock_repo.get.assert_called_once_with(job.job_id)
    
    def test_get_job_raises_error_when_job_not_found(self):
        """
        Test that get_job() raises JobNotFoundError when job doesn't exist.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get.return_value = None
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(JobNotFoundError) as exc_info:
            manager.get_job("nonexistent-job-id")
        assert "Job nonexistent-job-id not found" in str(exc_info.value)
    
    def test_start_job_transitions_job_to_processing(self):
        """
        Test that start_job() transitions a pending job to processing.
        
        Verifies:
        - Job status changes to PROCESSING
        - Job is saved to repository
        - Updated job is returned
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        mock_repo.get.return_value = job
        mock_repo.save.return_value = True
        manager = JobManager(mock_repo)
        
        # Act
        updated_job = manager.start_job(job.job_id)
        
        # Assert
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.progress.phase == "extracting metadata"
        mock_repo.save.assert_called_once()
    
    def test_start_job_raises_error_when_job_not_found(self):
        """
        Test that start_job() raises JobNotFoundError when job doesn't exist.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get.return_value = None
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            manager.start_job("nonexistent-job-id")
    
    def test_start_job_raises_error_when_invalid_state_transition(self):
        """
        Test that start_job() raises JobStateError for invalid state transitions.
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()  # Move to COMPLETED state
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(JobStateError) as exc_info:
            manager.start_job(job.job_id)
        assert "Cannot start job in completed state" in str(exc_info.value)
    
    def test_update_job_progress_updates_progress_atomically(self):
        """
        Test that update_job_progress() updates progress atomically.
        
        Verifies:
        - Repository update_progress() is called
        - Returns True on success
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        mock_repo.exists.return_value = True
        mock_repo.update_progress.return_value = True
        manager = JobManager(mock_repo)
        
        new_progress = JobProgress.downloading(50, speed="1.5 MiB/s")
        
        # Act
        result = manager.update_job_progress(job.job_id, new_progress)
        
        # Assert
        assert result is True
        mock_repo.update_progress.assert_called_once_with(job.job_id, new_progress)
    
    def test_update_job_progress_raises_error_when_job_not_found(self):
        """
        Test that update_job_progress() raises JobNotFoundError when job doesn't exist.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.exists.return_value = False
        manager = JobManager(mock_repo)
        
        new_progress = JobProgress.downloading(50)
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            manager.update_job_progress("nonexistent-job-id", new_progress)
    
    def test_complete_job_marks_job_as_completed(self):
        """
        Test that complete_job() marks a processing job as completed.
        
        Verifies:
        - Job status changes to COMPLETED
        - Download information is set
        - Job is saved to repository
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()  # Move to PROCESSING
        mock_repo.get.return_value = job
        mock_repo.save.return_value = True
        manager = JobManager(mock_repo)
        
        download_url = "https://example.com/file.mp4"
        download_token = "test_token_" + "a" * 22
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Act
        completed_job = manager.complete_job(
            job.job_id,
            download_url=download_url,
            download_token=download_token,
            expire_at=expire_at
        )
        
        # Assert
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.download_url == download_url
        assert completed_job.expire_at == expire_at
        mock_repo.save.assert_called_once()
    
    def test_complete_job_raises_error_when_job_not_found(self):
        """
        Test that complete_job() raises JobNotFoundError when job doesn't exist.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get.return_value = None
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            manager.complete_job("nonexistent-job-id")
    
    def test_complete_job_raises_error_when_invalid_state(self):
        """
        Test that complete_job() raises JobStateError when job is not processing.
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        # Job is PENDING, not PROCESSING
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(JobStateError) as exc_info:
            manager.complete_job(job.job_id)
        assert "Cannot complete job in pending state" in str(exc_info.value)
    
    def test_fail_job_marks_job_as_failed(self):
        """
        Test that fail_job() marks a job as failed with error details.
        
        Verifies:
        - Job status changes to FAILED
        - Error message and category are set
        - Job is saved to repository
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        mock_repo.get.return_value = job
        mock_repo.save.return_value = True
        manager = JobManager(mock_repo)
        
        error_message = "Video unavailable"
        error_category = "VIDEO_UNAVAILABLE"
        
        # Act
        failed_job = manager.fail_job(job.job_id, error_message, error_category)
        
        # Assert
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error_message == error_message
        assert failed_job.error_category == error_category
        mock_repo.save.assert_called_once()
    
    def test_fail_job_raises_error_when_job_not_found(self):
        """
        Test that fail_job() raises JobNotFoundError when job doesn't exist.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get.return_value = None
        manager = JobManager(mock_repo)
        
        # Act & Assert
        with pytest.raises(JobNotFoundError):
            manager.fail_job("nonexistent-job-id", "Error message")
    
    def test_delete_job_deletes_from_repository(self):
        """
        Test that delete_job() deletes job from repository.
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.delete.return_value = True
        manager = JobManager(mock_repo)
        
        job_id = "test-job-id"
        
        # Act
        result = manager.delete_job(job_id)
        
        # Assert
        assert result is True
        mock_repo.delete.assert_called_once_with(job_id)
    
    def test_cleanup_expired_jobs_with_archival_flow(self):
        """
        Test that cleanup_expired_jobs() follows archival flow.
        
        Verifies:
        1. Get expired job IDs
        2. Get job data
        3. Create and save archive
        4. Delete file via FileManager
        5. Delete job record
        6. Return count of cleaned jobs
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        mock_file_manager = Mock()
        
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        mock_repo.get_expired_jobs.return_value = [job.job_id]
        mock_repo.get.return_value = job
        mock_archive_repo.save.return_value = True
        mock_file_manager.delete_file_by_job_id.return_value = True
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=mock_file_manager
        )
        
        # Assert
        assert count == 1
        mock_repo.get_expired_jobs.assert_called_once()
        mock_repo.get.assert_called_once_with(job.job_id)
        mock_archive_repo.save.assert_called_once()
        mock_file_manager.delete_file_by_job_id.assert_called_once_with(job.job_id)
        mock_repo.delete.assert_called_once_with(job.job_id)
    
    def test_cleanup_handles_individual_failures_gracefully(self):
        """
        Test that cleanup continues processing other jobs when one fails.
        
        Verifies that individual cleanup failures don't block other cleanups.
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        mock_file_manager = Mock()
        
        job1 = DownloadJob.create("https://youtube.com/watch?v=test1", "best")
        job1.start()
        job1.complete()
        
        job2 = DownloadJob.create("https://youtube.com/watch?v=test2", "best")
        job2.start()
        job2.complete()
        
        mock_repo.get_expired_jobs.return_value = [job1.job_id, job2.job_id]
        mock_repo.get.side_effect = [job1, job2]
        # First archive fails, second succeeds
        mock_archive_repo.save.side_effect = [Exception("Archive failed"), True]
        mock_file_manager.delete_file_by_job_id.return_value = True
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=mock_file_manager
        )
        
        # Assert - both jobs should be processed despite first archive failure
        assert count == 2
        assert mock_repo.get.call_count == 2
        assert mock_archive_repo.save.call_count == 2
        assert mock_file_manager.delete_file_by_job_id.call_count == 2
        assert mock_repo.delete.call_count == 2
    
    def test_cleanup_continues_when_archive_fails(self):
        """
        Test that cleanup continues with file deletion and job deletion when archive fails.
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        mock_file_manager = Mock()
        
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        mock_repo.get_expired_jobs.return_value = [job.job_id]
        mock_repo.get.return_value = job
        mock_archive_repo.save.side_effect = Exception("Archive failed")
        mock_file_manager.delete_file_by_job_id.return_value = True
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=mock_file_manager
        )
        
        # Assert - cleanup should succeed despite archive failure
        assert count == 1
        mock_file_manager.delete_file_by_job_id.assert_called_once()
        mock_repo.delete.assert_called_once()
    
    def test_cleanup_continues_when_file_deletion_fails(self):
        """
        Test that cleanup continues with job deletion when file deletion fails.
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        mock_file_manager = Mock()
        
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        mock_repo.get_expired_jobs.return_value = [job.job_id]
        mock_repo.get.return_value = job
        mock_archive_repo.save.return_value = True
        mock_file_manager.delete_file_by_job_id.side_effect = Exception("File deletion failed")
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=mock_file_manager
        )
        
        # Assert - cleanup should succeed despite file deletion failure
        assert count == 1
        mock_archive_repo.save.assert_called_once()
        mock_repo.delete.assert_called_once()
    
    def test_cleanup_skips_already_deleted_jobs(self):
        """
        Test that cleanup handles jobs that are already deleted.
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        
        mock_repo.get_expired_jobs.return_value = ["deleted-job-id"]
        mock_repo.get.return_value = None  # Job already deleted
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(expiration_time=timedelta(hours=1))
        
        # Assert - should skip without error
        assert count == 0
        mock_archive_repo.save.assert_not_called()
        mock_repo.delete.assert_not_called()
    
    def test_cleanup_without_archive_repository(self):
        """
        Test that cleanup works when archive repository is not provided.
        """
        # Arrange
        mock_repo = Mock()
        mock_file_manager = Mock()
        
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        mock_repo.get_expired_jobs.return_value = [job.job_id]
        mock_repo.get.return_value = job
        mock_file_manager.delete_file_by_job_id.return_value = True
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, archive_repository=None)
        
        # Act
        count = manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=mock_file_manager
        )
        
        # Assert - cleanup should work without archival
        assert count == 1
        mock_file_manager.delete_file_by_job_id.assert_called_once()
        mock_repo.delete.assert_called_once()
    
    def test_cleanup_without_file_manager(self):
        """
        Test that cleanup works when file manager is not provided.
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        mock_repo.get_expired_jobs.return_value = [job.job_id]
        mock_repo.get.return_value = job
        mock_archive_repo.save.return_value = True
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=None
        )
        
        # Assert - cleanup should work without file deletion
        assert count == 1
        mock_archive_repo.save.assert_called_once()
        mock_repo.delete.assert_called_once()
    
    def test_cleanup_skips_archival_for_non_terminal_jobs(self):
        """
        Test that cleanup only archives terminal jobs.
        """
        # Arrange
        mock_repo = Mock()
        mock_archive_repo = Mock()
        
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()  # PROCESSING state (non-terminal)
        
        mock_repo.get_expired_jobs.return_value = [job.job_id]
        mock_repo.get.return_value = job
        mock_repo.delete.return_value = True
        
        manager = JobManager(mock_repo, mock_archive_repo)
        
        # Act
        count = manager.cleanup_expired_jobs(expiration_time=timedelta(hours=1))
        
        # Assert - job should be deleted but not archived
        assert count == 1
        mock_archive_repo.save.assert_not_called()
        mock_repo.delete.assert_called_once()
    
    def test_get_job_status_info_returns_complete_information(self):
        """
        Test that get_job_status_info() returns all job status information.
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        download_url = "https://example.com/file.mp4"
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        job.complete(download_url=download_url, expire_at=expire_at)
        
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act
        info = manager.get_job_status_info(job.job_id)
        
        # Assert
        assert info["job_id"] == job.job_id
        assert info["status"] == "completed"
        assert info["progress"]["percentage"] == 100
        assert info["download_url"] == download_url
        assert info["expire_at"] == expire_at.isoformat()
        assert info["time_remaining"] is not None
        assert info["error"] is None
        assert info["error_category"] is None
    
    def test_get_job_status_info_includes_error_details_for_failed_jobs(self):
        """
        Test that get_job_status_info() includes error details for failed jobs.
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        error_message = "Video unavailable"
        error_category = "VIDEO_UNAVAILABLE"
        job.fail(error_message, error_category)
        
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act
        info = manager.get_job_status_info(job.job_id)
        
        # Assert
        assert info["status"] == "failed"
        assert info["error"] == error_message
        assert info["error_category"] == error_category
    
    def test_get_job_status_info_calculates_time_remaining(self):
        """
        Test that get_job_status_info() calculates time remaining correctly.
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        expire_at = datetime.utcnow() + timedelta(minutes=5)
        job.complete(expire_at=expire_at)
        
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act
        info = manager.get_job_status_info(job.job_id)
        
        # Assert
        assert info["time_remaining"] is not None
        assert info["time_remaining"] > 0
        assert info["time_remaining"] <= 300  # 5 minutes in seconds
    
    def test_get_job_status_info_returns_zero_for_expired_jobs(self):
        """
        Test that get_job_status_info() returns 0 time remaining for expired jobs.
        """
        # Arrange
        mock_repo = Mock()
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        expire_at = datetime.utcnow() - timedelta(minutes=5)  # Already expired
        job.complete(expire_at=expire_at)
        
        mock_repo.get.return_value = job
        manager = JobManager(mock_repo)
        
        # Act
        info = manager.get_job_status_info(job.job_id)
        
        # Assert
        assert info["time_remaining"] == 0
