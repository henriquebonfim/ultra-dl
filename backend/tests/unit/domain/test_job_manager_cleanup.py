"""
Unit tests for JobManager cleanup functionality.

Tests verify that cleanup_expired_jobs meets all requirements:
- Accepts archive_repo and file_manager parameters
- Implements archival flow: get job → create archive → save archive → delete file → delete job
- Returns count of successfully cleaned jobs
- Handles individual cleanup failures gracefully
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, call
import pytest

from src.domain.job_management.services import JobManager
from src.domain.job_management.entities import DownloadJob, JobArchive
from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.video_processing.value_objects import FormatId
from src.domain.file_storage.value_objects import DownloadToken


# Helper to create valid tokens for testing
def create_test_token(suffix: str = "1") -> DownloadToken:
    """Create a valid test token (32+ characters)."""
    return DownloadToken(f"test_token_{'0' * 20}_{suffix}")


class TestJobManagerCleanup:
    """Test JobManager cleanup_expired_jobs functionality."""

    def test_cleanup_with_archival_and_file_deletion(self):
        """Test complete cleanup flow with archival and file deletion."""
        # Arrange
        job_repo = Mock()
        archive_repo = Mock()
        file_manager = Mock()
        
        job_manager = JobManager(job_repo, archive_repo)
        
        # Create a completed job
        job = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("1")
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1"]
        job_repo.get.return_value = job
        archive_repo.save.return_value = True
        file_manager.delete_file_by_job_id.return_value = True
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=file_manager
        )
        
        # Assert
        assert count == 1
        
        # Verify archival happened
        archive_repo.save.assert_called_once()
        saved_archive = archive_repo.save.call_args[0][0]
        assert isinstance(saved_archive, JobArchive)
        assert saved_archive.job_id == "job-1"
        
        # Verify file deletion happened with job_id
        file_manager.delete_file_by_job_id.assert_called_once_with("job-1")
        
        # Verify job deletion happened
        job_repo.delete.assert_called_once_with("job-1")

    def test_cleanup_continues_on_archive_failure(self):
        """Test that cleanup continues even if archival fails."""
        # Arrange
        job_repo = Mock()
        archive_repo = Mock()
        file_manager = Mock()
        
        job_manager = JobManager(job_repo, archive_repo)
        
        job = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("1")
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1"]
        job_repo.get.return_value = job
        archive_repo.save.side_effect = Exception("Archive failed")
        file_manager.delete_file_by_job_id.return_value = True
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=file_manager
        )
        
        # Assert - cleanup should still succeed
        assert count == 1
        file_manager.delete_file_by_job_id.assert_called_once()
        job_repo.delete.assert_called_once()

    def test_cleanup_continues_on_file_deletion_failure(self):
        """Test that cleanup continues even if file deletion fails."""
        # Arrange
        job_repo = Mock()
        archive_repo = Mock()
        file_manager = Mock()
        
        job_manager = JobManager(job_repo, archive_repo)
        
        job = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("1")
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1"]
        job_repo.get.return_value = job
        archive_repo.save.return_value = True
        file_manager.delete_file_by_job_id.side_effect = Exception("File deletion failed")
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=file_manager
        )
        
        # Assert - cleanup should still succeed
        assert count == 1
        archive_repo.save.assert_called_once()
        job_repo.delete.assert_called_once()

    def test_cleanup_handles_multiple_jobs_with_partial_failures(self):
        """Test that cleanup processes all jobs even when some fail."""
        # Arrange
        job_repo = Mock()
        archive_repo = Mock()
        file_manager = Mock()
        
        job_manager = JobManager(job_repo, archive_repo)
        
        job1 = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test1",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("1")
        )
        
        job2 = DownloadJob(
            job_id="job-2",
            url="https://youtube.com/watch?v=test2",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("2")
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1", "job-2"]
        job_repo.get.side_effect = [job1, job2]
        archive_repo.save.side_effect = [Exception("Archive failed"), True]
        file_manager.delete_file_by_job_id.return_value = True
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=file_manager
        )
        
        # Assert - both jobs should be processed
        assert count == 2
        assert archive_repo.save.call_count == 2
        assert file_manager.delete_file_by_job_id.call_count == 2
        assert job_repo.delete.call_count == 2

    def test_cleanup_without_archive_repo(self):
        """Test cleanup works when archive_repo is None."""
        # Arrange
        job_repo = Mock()
        file_manager = Mock()
        
        job_manager = JobManager(job_repo, archive_repository=None)
        
        job = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("1")
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1"]
        job_repo.get.return_value = job
        file_manager.delete_file_by_job_id.return_value = True
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=file_manager
        )
        
        # Assert - cleanup should work without archival
        assert count == 1
        file_manager.delete_file_by_job_id.assert_called_once()
        job_repo.delete.assert_called_once()

    def test_cleanup_without_file_manager(self):
        """Test cleanup works when file_manager is None."""
        # Arrange
        job_repo = Mock()
        archive_repo = Mock()
        
        job_manager = JobManager(job_repo, archive_repo)
        
        job = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
            download_token=create_test_token("1")
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1"]
        job_repo.get.return_value = job
        archive_repo.save.return_value = True
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=None
        )
        
        # Assert - cleanup should work without file deletion
        assert count == 1
        archive_repo.save.assert_called_once()
        job_repo.delete.assert_called_once()

    def test_cleanup_skips_non_terminal_jobs(self):
        """Test that archival only happens for terminal jobs."""
        # Arrange
        job_repo = Mock()
        archive_repo = Mock()
        file_manager = Mock()
        
        job_manager = JobManager(job_repo, archive_repo)
        
        # Create a processing job (non-terminal)
        job = DownloadJob(
            job_id="job-1",
            url="https://youtube.com/watch?v=test",
            format_id=FormatId("best"),
            status=JobStatus.PROCESSING,
            progress=JobProgress.metadata_extraction(),
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        job_repo.get_expired_jobs.return_value = ["job-1"]
        job_repo.get.return_value = job
        file_manager.delete_file_by_job_id.return_value = True
        job_repo.delete.return_value = True
        
        # Act
        count = job_manager.cleanup_expired_jobs(
            expiration_time=timedelta(hours=1),
            file_manager=file_manager
        )
        
        # Assert - job should be deleted but not archived
        assert count == 1
        archive_repo.save.assert_not_called()
        job_repo.delete.assert_called_once()
