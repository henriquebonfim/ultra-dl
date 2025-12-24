"""
Unit tests for job management entities.

Tests verify DownloadJob and JobArchive entity behavior including:
- Factory methods and initialization
- State transitions and lifecycle management
- Serialization and deserialization
- Invariant enforcement

Requirements: 1.1, 1.4
"""

import pytest
from datetime import datetime, timedelta
from src.domain.job_management.entities import DownloadJob, JobArchive
from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.video_processing.value_objects import FormatId
from src.domain.file_storage.value_objects import DownloadToken
from src.domain.events import JobStartedEvent, JobCompletedEvent, JobFailedEvent


class TestDownloadJobEntity:
    """Test DownloadJob entity behavior."""
    
    def test_factory_method_creates_job_with_correct_initial_state(self):
        """
        Test that DownloadJob.create() initializes a job with correct defaults.
        
        Verifies:
        - Job ID is generated (UUID format)
        - Status is PENDING
        - Progress is initial state
        - Timestamps are set
        - URL and format_id are preserved
        """
        # Arrange
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        format_id = "best"
        
        # Act
        job = DownloadJob.create(url, format_id)
        
        # Assert
        assert job.job_id is not None
        assert len(job.job_id) == 36  # UUID format
        assert job.url == url
        assert isinstance(job.format_id, FormatId)
        assert str(job.format_id) == format_id
        assert job.status == JobStatus.PENDING
        assert job.progress.percentage == 0
        assert job.progress.phase == "initializing"
        assert job.created_at is not None
        assert job.updated_at is not None
        assert job.created_at == job.updated_at
        assert job.error_message is None
        assert job.error_category is None
        assert job.download_url is None
        assert job.download_token is None
        assert job.expire_at is None
    
    def test_start_transitions_from_pending_to_processing(self):
        """
        Test that start() transitions job from PENDING to PROCESSING.
        
        Verifies:
        - Status changes to PROCESSING
        - Progress updates to metadata_extraction
        - updated_at timestamp is updated
        - JobStartedEvent is returned
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        original_updated_at = job.updated_at
        
        # Act
        event = job.start()
        
        # Assert
        assert job.status == JobStatus.PROCESSING
        assert job.progress.phase == "extracting metadata"
        assert job.progress.percentage == 5
        assert job.updated_at > original_updated_at
        assert isinstance(event, JobStartedEvent)
        assert event.aggregate_id == job.job_id
        assert event.url == job.url
        assert event.format_id == "best"
    
    def test_start_is_idempotent_when_already_processing(self):
        """
        Test that start() is idempotent when job is already processing.
        
        Verifies:
        - No state change occurs
        - No event is returned
        - Status remains PROCESSING
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()  # First start
        status_after_first_start = job.status
        updated_at_after_first_start = job.updated_at
        
        # Act
        event = job.start()  # Second start
        
        # Assert
        assert event is None
        assert job.status == status_after_first_start
        assert job.updated_at == updated_at_after_first_start
    
    def test_start_raises_error_when_job_completed(self):
        """
        Test that start() raises ValueError when job is already completed.
        
        Verifies:
        - ValueError is raised
        - Error message indicates invalid state
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            job.start()
        assert "Cannot start job in completed state" in str(exc_info.value)
    
    def test_start_raises_error_when_job_failed(self):
        """
        Test that start() raises ValueError when job has failed.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.fail("Test error")
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            job.start()
        assert "Cannot start job in failed state" in str(exc_info.value)
    
    def test_update_progress_updates_progress_and_timestamp(self):
        """
        Test that update_progress() updates progress and timestamp.
        
        Verifies:
        - Progress is updated
        - updated_at timestamp is updated
        - Job remains in PROCESSING state
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        original_updated_at = job.updated_at
        new_progress = JobProgress.downloading(50, speed="1.5 MiB/s", eta=60)
        
        # Act
        job.update_progress(new_progress)
        
        # Assert
        assert job.progress == new_progress
        assert job.progress.percentage == 50
        assert job.progress.phase == "downloading"
        assert job.progress.speed == "1.5 MiB/s"
        assert job.progress.eta == 60
        assert job.updated_at > original_updated_at
        assert job.status == JobStatus.PROCESSING
    
    def test_update_progress_raises_error_when_not_processing(self):
        """
        Test that update_progress() raises ValueError when job is not processing.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        new_progress = JobProgress.downloading(50)
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            job.update_progress(new_progress)
        assert "Cannot update progress for job in pending state" in str(exc_info.value)
    
    def test_complete_transitions_to_completed_with_download_info(self):
        """
        Test that complete() transitions job to COMPLETED with download information.
        
        Verifies:
        - Status changes to COMPLETED
        - Progress updates to completed state
        - Download URL, token, and expiration are set
        - updated_at timestamp is updated
        - JobCompletedEvent is returned
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        original_updated_at = job.updated_at
        download_url = "https://example.com/download/file.mp4"
        download_token = DownloadToken.generate()
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Act
        event = job.complete(download_url, download_token, expire_at)
        
        # Assert
        assert job.status == JobStatus.COMPLETED
        assert job.progress.percentage == 100
        assert job.progress.phase == "completed"
        assert job.download_url == download_url
        assert job.download_token == download_token
        assert job.expire_at == expire_at
        assert job.updated_at > original_updated_at
        assert isinstance(event, JobCompletedEvent)
        assert event.aggregate_id == job.job_id
        assert event.download_url == download_url
        assert event.expire_at == expire_at
    
    def test_complete_raises_error_when_not_processing(self):
        """
        Test that complete() raises ValueError when job is not processing.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            job.complete()
        assert "Cannot complete job in pending state" in str(exc_info.value)
    
    def test_fail_transitions_to_failed_with_error_details(self):
        """
        Test that fail() transitions job to FAILED with error information.
        
        Verifies:
        - Status changes to FAILED
        - Error message is set
        - Error category is set (if provided)
        - updated_at timestamp is updated
        - JobFailedEvent is returned
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        original_updated_at = job.updated_at
        error_message = "Video unavailable"
        error_category = "VIDEO_UNAVAILABLE"
        
        # Act
        event = job.fail(error_message, error_category)
        
        # Assert
        assert job.status == JobStatus.FAILED
        assert job.error_message == error_message
        assert job.error_category == error_category
        assert job.updated_at > original_updated_at
        assert isinstance(event, JobFailedEvent)
        assert event.aggregate_id == job.job_id
        assert event.error_message == error_message
        assert event.error_category == error_category
    
    def test_fail_can_be_called_from_any_state(self):
        """
        Test that fail() can be called from any job state.
        
        Verifies that jobs can fail at any point in their lifecycle.
        """
        # Test from PENDING
        job1 = DownloadJob.create("https://youtube.com/watch?v=test1", "best")
        event1 = job1.fail("Error in pending")
        assert job1.status == JobStatus.FAILED
        assert isinstance(event1, JobFailedEvent)
        
        # Test from PROCESSING
        job2 = DownloadJob.create("https://youtube.com/watch?v=test2", "best")
        job2.start()
        event2 = job2.fail("Error in processing")
        assert job2.status == JobStatus.FAILED
        assert isinstance(event2, JobFailedEvent)
    
    def test_is_terminal_returns_true_for_completed(self):
        """
        Test that is_terminal() returns True for completed jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        # Act & Assert
        assert job.is_terminal() is True
    
    def test_is_terminal_returns_true_for_failed(self):
        """
        Test that is_terminal() returns True for failed jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.fail("Test error")
        
        # Act & Assert
        assert job.is_terminal() is True
    
    def test_is_terminal_returns_false_for_pending(self):
        """
        Test that is_terminal() returns False for pending jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        
        # Act & Assert
        assert job.is_terminal() is False
    
    def test_is_terminal_returns_false_for_processing(self):
        """
        Test that is_terminal() returns False for processing jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        
        # Act & Assert
        assert job.is_terminal() is False
    
    def test_is_active_returns_true_for_pending(self):
        """
        Test that is_active() returns True for pending jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        
        # Act & Assert
        assert job.is_active() is True
    
    def test_is_active_returns_true_for_processing(self):
        """
        Test that is_active() returns True for processing jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        
        # Act & Assert
        assert job.is_active() is True
    
    def test_is_active_returns_false_for_completed(self):
        """
        Test that is_active() returns False for completed jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        
        # Act & Assert
        assert job.is_active() is False
    
    def test_is_active_returns_false_for_failed(self):
        """
        Test that is_active() returns False for failed jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.fail("Test error")
        
        # Act & Assert
        assert job.is_active() is False
    
    def test_to_dict_serialization(self):
        """
        Test that to_dict() correctly serializes job to dictionary.
        
        Verifies all fields are included and properly formatted.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        download_token = DownloadToken.generate()
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        job.complete("https://example.com/file.mp4", download_token, expire_at)
        
        # Act
        data = job.to_dict()
        
        # Assert
        assert data["job_id"] == job.job_id
        assert data["url"] == job.url
        assert data["format_id"] == "best"
        assert data["status"] == "completed"
        assert "progress" in data
        assert data["progress"]["percentage"] == 100
        assert data["created_at"] == job.created_at.isoformat()
        assert data["updated_at"] == job.updated_at.isoformat()
        assert data["download_url"] == "https://example.com/file.mp4"
        assert data["download_token"] == str(download_token)
        assert data["expire_at"] == expire_at.isoformat()
    
    def test_from_dict_deserialization(self):
        """
        Test that from_dict() correctly deserializes job from dictionary.
        
        Verifies round-trip serialization preserves all data.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        download_token = DownloadToken.generate()
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        job.complete("https://example.com/file.mp4", download_token, expire_at)
        data = job.to_dict()
        
        # Act
        restored_job = DownloadJob.from_dict(data)
        
        # Assert
        assert restored_job.job_id == job.job_id
        assert restored_job.url == job.url
        assert str(restored_job.format_id) == str(job.format_id)
        assert restored_job.status == job.status
        assert restored_job.progress.percentage == job.progress.percentage
        assert restored_job.progress.phase == job.progress.phase
        assert restored_job.created_at == job.created_at
        assert restored_job.updated_at == job.updated_at
        assert restored_job.download_url == job.download_url
        assert str(restored_job.download_token) == str(job.download_token)
        assert restored_job.expire_at == job.expire_at
    
    def test_from_dict_handles_optional_fields(self):
        """
        Test that from_dict() handles missing optional fields correctly.
        """
        # Arrange
        data = {
            "job_id": "test-job-id",
            "url": "https://youtube.com/watch?v=test",
            "format_id": "best",
            "status": "pending",
            "progress": {"percentage": 0, "phase": "initializing"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Act
        job = DownloadJob.from_dict(data)
        
        # Assert
        assert job.job_id == "test-job-id"
        assert job.error_message is None
        assert job.error_category is None
        assert job.download_url is None
        assert job.download_token is None
        assert job.expire_at is None
    
    def test_created_at_never_changes(self):
        """
        Test that created_at timestamp remains constant through state transitions.
        
        Verifies the invariant that creation time is immutable.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        original_created_at = job.created_at
        
        # Act - perform various state transitions
        job.start()
        job.update_progress(JobProgress.downloading(50))
        job.complete()
        
        # Assert
        assert job.created_at == original_created_at
    
    def test_updated_at_increases_monotonically(self):
        """
        Test that updated_at timestamp increases with each state change.
        
        Verifies the invariant that updates are chronologically ordered.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        timestamps = [job.updated_at]
        
        # Act
        job.start()
        timestamps.append(job.updated_at)
        
        job.update_progress(JobProgress.downloading(50))
        timestamps.append(job.updated_at)
        
        job.complete()
        timestamps.append(job.updated_at)
        
        # Assert - each timestamp should be >= previous
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]


class TestJobArchiveEntity:
    """Test JobArchive entity behavior."""
    
    def test_from_job_creates_archive_with_complete_metadata(self):
        """
        Test that from_job() creates archive with all essential metadata.
        
        Verifies:
        - All job fields are preserved
        - archived_at timestamp is set
        - Archive is immutable snapshot
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        download_token = DownloadToken.generate()
        job.complete("https://example.com/file.mp4", download_token, datetime.utcnow() + timedelta(minutes=10))
        
        # Act
        archive = JobArchive.from_job(job)
        
        # Assert
        assert archive.job_id == job.job_id
        assert archive.url == job.url
        assert archive.format_id == str(job.format_id)
        assert archive.status == job.status.value
        assert archive.created_at == job.created_at
        assert archive.completed_at == job.updated_at
        assert archive.archived_at is not None
        assert archive.archived_at >= job.updated_at
        assert archive.error_message is None
        assert archive.error_category is None
        assert archive.download_token == str(download_token)
    
    def test_from_job_preserves_error_details_for_failed_jobs(self):
        """
        Test that from_job() preserves error information for failed jobs.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.fail("Video unavailable", "VIDEO_UNAVAILABLE")
        
        # Act
        archive = JobArchive.from_job(job)
        
        # Assert
        assert archive.status == "failed"
        assert archive.error_message == "Video unavailable"
        assert archive.error_category == "VIDEO_UNAVAILABLE"
    
    def test_from_job_raises_error_for_non_terminal_jobs(self):
        """
        Test that from_job() raises ValueError for non-terminal jobs.
        
        Verifies that only completed or failed jobs can be archived.
        """
        # Test with PENDING job
        job_pending = DownloadJob.create("https://youtube.com/watch?v=test1", "best")
        with pytest.raises(ValueError) as exc_info:
            JobArchive.from_job(job_pending)
        assert "Cannot archive job in pending state" in str(exc_info.value)
        assert "terminal state" in str(exc_info.value)
        
        # Test with PROCESSING job
        job_processing = DownloadJob.create("https://youtube.com/watch?v=test2", "best")
        job_processing.start()
        with pytest.raises(ValueError) as exc_info:
            JobArchive.from_job(job_processing)
        assert "Cannot archive job in processing state" in str(exc_info.value)
        assert "terminal state" in str(exc_info.value)
    
    def test_to_dict_serialization(self):
        """
        Test that to_dict() correctly serializes archive to dictionary.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        archive = JobArchive.from_job(job)
        
        # Act
        data = archive.to_dict()
        
        # Assert
        assert data["job_id"] == archive.job_id
        assert data["url"] == archive.url
        assert data["format_id"] == archive.format_id
        assert data["status"] == archive.status
        assert data["created_at"] == archive.created_at.isoformat()
        assert data["completed_at"] == archive.completed_at.isoformat()
        assert data["archived_at"] == archive.archived_at.isoformat()
    
    def test_from_dict_deserialization(self):
        """
        Test that from_dict() correctly deserializes archive from dictionary.
        
        Verifies round-trip serialization preserves all data.
        """
        # Arrange
        job = DownloadJob.create("https://youtube.com/watch?v=test", "best")
        job.start()
        job.complete()
        archive = JobArchive.from_job(job)
        data = archive.to_dict()
        
        # Act
        restored_archive = JobArchive.from_dict(data)
        
        # Assert
        assert restored_archive.job_id == archive.job_id
        assert restored_archive.url == archive.url
        assert restored_archive.format_id == archive.format_id
        assert restored_archive.status == archive.status
        assert restored_archive.created_at == archive.created_at
        assert restored_archive.completed_at == archive.completed_at
        assert restored_archive.archived_at == archive.archived_at
        assert restored_archive.error_message == archive.error_message
        assert restored_archive.error_category == archive.error_category
        assert restored_archive.download_token == archive.download_token
    
    def test_from_dict_handles_optional_fields(self):
        """
        Test that from_dict() handles missing optional fields correctly.
        """
        # Arrange
        data = {
            "job_id": "test-job-id",
            "url": "https://youtube.com/watch?v=test",
            "format_id": "best",
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "archived_at": datetime.utcnow().isoformat(),
        }
        
        # Act
        archive = JobArchive.from_dict(data)
        
        # Assert
        assert archive.job_id == "test-job-id"
        assert archive.error_message is None
        assert archive.error_category is None
        assert archive.download_token is None
