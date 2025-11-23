"""
Unit Tests for Cleanup Task

Tests Celery beat task for periodic cleanup of expired jobs and files.
Tests that tasks only access infrastructure through application services.
Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.3, 6.5, 9.4
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call


class TestCleanupTaskUnit(unittest.TestCase):
    """Unit tests with mocked services."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        self.mock_app = Mock()
        self.mock_app_context = MagicMock()
        self.mock_job_service = Mock()
        self.mock_file_manager = Mock()
        self.mock_gcs_repo = Mock()
        
        # Configure app context manager
        self.mock_app.__enter__ = Mock(return_value=self.mock_app)
        self.mock_app.__exit__ = Mock(return_value=False)
        self.mock_app_context.return_value = self.mock_app
        
        # Configure mock container
        from application.job_service import JobService
        from domain.file_storage import FileManager
        mock_container = Mock()
        mock_container.resolve = Mock(side_effect=lambda cls: {
            JobService: self.mock_job_service,
            FileManager: self.mock_file_manager
        }.get(cls, Mock()))
        self.mock_app.container = mock_container
    
    def test_cleanup_expired_jobs_calls_file_manager(self):
        """Test task calls file_manager.cleanup_expired_files.
        
        Requirements: 5.2, 5.3
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    # Configure mocks
                    self.mock_file_manager.file_repo.get_expired_files.return_value = []
                    self.mock_file_manager.cleanup_expired_files.return_value = 5
                    self.mock_job_service.cleanup_expired_jobs.return_value = 3
                    
                    # Import and call the task
                    from tasks.cleanup_task import cleanup_expired_jobs
                    result = cleanup_expired_jobs()
                    
                    # Verify file_manager.cleanup_expired_files was called
                    self.mock_file_manager.cleanup_expired_files.assert_called_once()
                    
                    # Verify result includes file cleanup count
                    self.assertEqual(result['expired_files_removed'], 5)
    
    def test_cleanup_expired_jobs_calls_job_service(self):
        """Test task calls job_service.cleanup_expired_jobs.
        
        Requirements: 5.2, 5.4
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    # Configure mocks
                    self.mock_file_manager.file_repo.get_expired_files.return_value = []
                    self.mock_file_manager.cleanup_expired_files.return_value = 2
                    self.mock_job_service.cleanup_expired_jobs.return_value = 7
                    
                    # Import and call the task
                    from tasks.cleanup_task import cleanup_expired_jobs
                    result = cleanup_expired_jobs()
                    
                    # Verify job_service.cleanup_expired_jobs was called with correct parameter
                    self.mock_job_service.cleanup_expired_jobs.assert_called_once_with(expiration_hours=1)
                    
                    # Verify result includes job cleanup count
                    self.assertEqual(result['expired_jobs_removed'], 7)
    
    def test_cleanup_expired_jobs_handles_gcs_files(self):
        """Test task handles GCS files when available.
        
        Requirements: 5.2, 5.3
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    # Create mock expired files with GCS paths
                    mock_file1 = Mock()
                    mock_file1.file_path = "downloads/job-123/video.mp4"
                    mock_file2 = Mock()
                    mock_file2.file_path = "downloads/job-456/audio.m4a"
                    mock_file3 = Mock()
                    mock_file3.file_path = "/tmp/local-file.mp4"
                    
                    # Configure mocks
                    self.mock_file_manager.file_repo.get_expired_files.return_value = [
                        mock_file1, mock_file2, mock_file3
                    ]
                    self.mock_file_manager.cleanup_expired_files.return_value = 3
                    self.mock_job_service.cleanup_expired_jobs.return_value = 2
                    self.mock_gcs_repo.is_available.return_value = True
                    self.mock_gcs_repo.delete_blob.return_value = True
                    
                    # Import and call the task
                    from tasks.cleanup_task import cleanup_expired_jobs
                    result = cleanup_expired_jobs()
                    
                    # Verify GCS delete was called for GCS files only
                    self.assertEqual(self.mock_gcs_repo.delete_blob.call_count, 2)
                    self.mock_gcs_repo.delete_blob.assert_any_call("downloads/job-123/video.mp4")
                    self.mock_gcs_repo.delete_blob.assert_any_call("downloads/job-456/audio.m4a")
    
    def test_cleanup_expired_jobs_returns_statistics_dict(self):
        """Test task returns statistics dict with correct structure.
        
        Requirements: 5.2, 5.5
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', return_value=4):
                        # Configure mocks
                        self.mock_file_manager.file_repo.get_expired_files.return_value = []
                        self.mock_file_manager.cleanup_expired_files.return_value = 10
                        self.mock_job_service.cleanup_expired_jobs.return_value = 8
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify result structure
                        self.assertIsInstance(result, dict)
                        self.assertIn('expired_jobs_removed', result)
                        self.assertIn('expired_files_removed', result)
                        self.assertIn('orphaned_files_cleaned', result)
                        self.assertIn('errors', result)
                        
                        # Verify values
                        self.assertEqual(result['expired_jobs_removed'], 8)
                        self.assertEqual(result['expired_files_removed'], 10)
                        self.assertEqual(result['orphaned_files_cleaned'], 4)
                        self.assertIsInstance(result['errors'], list)
    
    def test_cleanup_expired_jobs_handles_file_cleanup_errors_gracefully(self):
        """Test task handles file cleanup errors gracefully.
        
        Requirements: 5.5, 5.6
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', return_value=0):
                        # Configure file_manager to raise exception
                        self.mock_file_manager.file_repo.get_expired_files.side_effect = Exception("File cleanup error")
                        self.mock_job_service.cleanup_expired_jobs.return_value = 5
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify task didn't crash
                        self.assertIsInstance(result, dict)
                        
                        # Verify error was recorded
                        self.assertGreater(len(result['errors']), 0)
                        self.assertTrue(any('Error cleaning up expired files' in err for err in result['errors']))
                        
                        # Verify job cleanup still ran
                        self.assertEqual(result['expired_jobs_removed'], 5)
    
    def test_cleanup_expired_jobs_handles_job_cleanup_errors_gracefully(self):
        """Test task handles job cleanup errors gracefully.
        
        Requirements: 5.5, 5.6
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', return_value=0):
                        # Configure job_service to raise exception
                        self.mock_file_manager.file_repo.get_expired_files.return_value = []
                        self.mock_file_manager.cleanup_expired_files.return_value = 3
                        self.mock_job_service.cleanup_expired_jobs.side_effect = Exception("Job cleanup error")
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify task didn't crash
                        self.assertIsInstance(result, dict)
                        
                        # Verify error was recorded
                        self.assertGreater(len(result['errors']), 0)
                        self.assertTrue(any('Error cleaning up expired jobs' in err for err in result['errors']))
                        
                        # Verify file cleanup still ran
                        self.assertEqual(result['expired_files_removed'], 3)
    
    def test_cleanup_expired_jobs_logs_cleanup_statistics(self):
        """Test task logs cleanup statistics.
        
        Requirements: 5.6
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', return_value=2):
                        with patch('tasks.cleanup_task.logger') as mock_logger:
                            # Configure mocks
                            self.mock_file_manager.file_repo.get_expired_files.return_value = []
                            self.mock_file_manager.cleanup_expired_files.return_value = 6
                            self.mock_job_service.cleanup_expired_jobs.return_value = 4
                            
                            # Import and call the task
                            from tasks.cleanup_task import cleanup_expired_jobs
                            result = cleanup_expired_jobs()
                            
                            # Verify logging was called
                            self.assertTrue(mock_logger.info.called)
                            
                            # Verify cleanup summary was logged
                            log_calls = [str(call) for call in mock_logger.info.call_args_list]
                            summary_logged = any('Cleanup completed' in str(call) for call in log_calls)
                            self.assertTrue(summary_logged, "Cleanup summary should be logged")
    
    def test_cleanup_expired_jobs_handles_gcs_delete_failure(self):
        """Test task handles GCS delete failure and logs error.
        
        Requirements: 5.5, 5.6
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    # Create mock expired file with GCS path
                    mock_file = Mock()
                    mock_file.file_path = "downloads/job-123/video.mp4"
                    
                    # Configure mocks - GCS delete fails
                    self.mock_file_manager.file_repo.get_expired_files.return_value = [mock_file]
                    self.mock_file_manager.cleanup_expired_files.return_value = 1
                    self.mock_job_service.cleanup_expired_jobs.return_value = 0
                    self.mock_gcs_repo.is_available.return_value = True
                    self.mock_gcs_repo.delete_blob.return_value = False  # Deletion fails
                    
                    # Import and call the task
                    from tasks.cleanup_task import cleanup_expired_jobs
                    result = cleanup_expired_jobs()
                    
                    # Verify error was recorded
                    self.assertGreater(len(result['errors']), 0)
                    self.assertTrue(any('Failed to delete GCS blob' in err for err in result['errors']))
    
    def test_cleanup_expired_jobs_handles_gcs_unavailable(self):
        """Test task handles GCS unavailable scenario.
        
        Requirements: 5.5, 5.6
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task.logger') as mock_logger:
                        # Create mock expired file with GCS path
                        mock_file = Mock()
                        mock_file.file_path = "downloads/job-456/audio.m4a"
                        
                        # Configure mocks - GCS not available
                        self.mock_file_manager.file_repo.get_expired_files.return_value = [mock_file]
                        self.mock_file_manager.cleanup_expired_files.return_value = 1
                        self.mock_job_service.cleanup_expired_jobs.return_value = 0
                        self.mock_gcs_repo.is_available.return_value = False  # GCS not available
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify warning was logged
                        self.assertTrue(mock_logger.warning.called)
                        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                        gcs_warning = any('GCS not available' in str(call) for call in warning_calls)
                        self.assertTrue(gcs_warning, "GCS unavailable warning should be logged")
    
    def test_cleanup_expired_jobs_handles_orphaned_files_cleanup_error(self):
        """Test task handles orphaned files cleanup errors gracefully.
        
        Requirements: 5.5, 5.6
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', side_effect=Exception("Orphaned cleanup error")):
                        # Configure mocks
                        self.mock_file_manager.file_repo.get_expired_files.return_value = []
                        self.mock_file_manager.cleanup_expired_files.return_value = 2
                        self.mock_job_service.cleanup_expired_jobs.return_value = 3
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify task didn't crash
                        self.assertIsInstance(result, dict)
                        
                        # Verify error was recorded
                        self.assertGreater(len(result['errors']), 0)
                        self.assertTrue(any('Error cleaning up orphaned files' in err for err in result['errors']))
                        
                        # Verify other cleanups still ran
                        self.assertEqual(result['expired_files_removed'], 2)
                        self.assertEqual(result['expired_jobs_removed'], 3)
    
    def test_cleanup_task_uses_container_resolve(self):
        """Test task uses container.resolve() to get application services.
        
        Verifies that the task accesses services through the dependency container
        rather than directly instantiating them, maintaining proper layer separation.
        
        Requirements: 6.3, 6.5, 9.4
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', return_value=0):
                        # Configure mocks
                        self.mock_file_manager.file_repo.get_expired_files.return_value = []
                        self.mock_file_manager.cleanup_expired_files.return_value = 1
                        self.mock_job_service.cleanup_expired_jobs.return_value = 1
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify container.resolve was called for JobService
                        from application.job_service import JobService
                        from domain.file_storage import FileManager
                        
                        # Check that resolve was called with the correct service types
                        resolve_calls = self.mock_app.container.resolve.call_args_list
                        service_types = [call[0][0] for call in resolve_calls]
                        
                        self.assertIn(JobService, service_types, 
                                    "Task should resolve JobService from container")
                        self.assertIn(FileManager, service_types,
                                    "Task should resolve FileManager from container")
    
    def test_cleanup_task_only_calls_application_service_methods(self):
        """Test task only calls application service methods, not infrastructure directly.
        
        Verifies that the task layer doesn't bypass the application layer to access
        infrastructure repositories directly.
        
        Requirements: 6.1, 6.3, 9.4
        """
        with patch('tasks.cleanup_task.current_app', self.mock_app):
            with patch('tasks.cleanup_task.current_app.app_context', self.mock_app_context):
                with patch('tasks.cleanup_task.GCSRepository', return_value=self.mock_gcs_repo):
                    with patch('tasks.cleanup_task._cleanup_orphaned_files', return_value=0):
                        # Configure mocks
                        self.mock_file_manager.file_repo.get_expired_files.return_value = []
                        self.mock_file_manager.cleanup_expired_files.return_value = 5
                        self.mock_job_service.cleanup_expired_jobs.return_value = 3
                        
                        # Import and call the task
                        from tasks.cleanup_task import cleanup_expired_jobs
                        result = cleanup_expired_jobs()
                        
                        # Verify application service methods were called
                        self.mock_file_manager.cleanup_expired_files.assert_called_once()
                        self.mock_job_service.cleanup_expired_jobs.assert_called_once_with(
                            expiration_hours=1
                        )
                        
                        # Verify results came from application services
                        self.assertEqual(result['expired_files_removed'], 5)
                        self.assertEqual(result['expired_jobs_removed'], 3)
    


class TestCleanupOrphanedFilesHelper(unittest.TestCase):
    """Unit tests for _cleanup_orphaned_files helper function."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_ultra_dl_dir = Path(self.temp_dir) / "ultra-dl"
        self.test_ultra_dl_dir.mkdir()
    
    def tearDown(self):
        """Clean up test fixtures after each test."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_removes_files_older_than_1_hour(self):
        """Test removes files older than 1 hour.
        
        Requirements: 5.3
        """
        # Create an old file
        old_file = self.test_ultra_dl_dir / "old_file.mp4"
        old_file.touch()
        
        # Set modification time to 2 hours ago
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        os.utime(old_file, (two_hours_ago.timestamp(), two_hours_ago.timestamp()))
        
        # Patch the temp_dir path
        with patch('tasks.cleanup_task.Path') as mock_path:
            mock_path.return_value = self.test_ultra_dl_dir
            
            # Import and call the helper
            from tasks.cleanup_task import _cleanup_orphaned_files
            count = _cleanup_orphaned_files()
            
            # Verify file was removed
            self.assertFalse(old_file.exists())
            self.assertEqual(count, 1)
    
    def test_removes_directories_older_than_1_hour(self):
        """Test removes directories older than 1 hour.
        
        Requirements: 5.3
        """
        # Create an old directory with a file
        old_dir = self.test_ultra_dl_dir / "old_directory"
        old_dir.mkdir()
        (old_dir / "file.txt").touch()
        
        # Set modification time to 2 hours ago
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        os.utime(old_dir, (two_hours_ago.timestamp(), two_hours_ago.timestamp()))
        
        # Patch the temp_dir path
        with patch('tasks.cleanup_task.Path') as mock_path:
            mock_path.return_value = self.test_ultra_dl_dir
            
            # Import and call the helper
            from tasks.cleanup_task import _cleanup_orphaned_files
            count = _cleanup_orphaned_files()
            
            # Verify directory was removed
            self.assertFalse(old_dir.exists())
            self.assertEqual(count, 1)
    
    def test_removes_empty_directories_regardless_of_age(self):
        """Test removes empty directories regardless of age.
        
        Requirements: 5.3
        """
        # Create a recent empty directory
        empty_dir = self.test_ultra_dl_dir / "empty_directory"
        empty_dir.mkdir()
        
        # Patch the temp_dir path
        with patch('tasks.cleanup_task.Path') as mock_path:
            mock_path.return_value = self.test_ultra_dl_dir
            
            # Import and call the helper
            from tasks.cleanup_task import _cleanup_orphaned_files
            count = _cleanup_orphaned_files()
            
            # Verify empty directory was removed
            self.assertFalse(empty_dir.exists())
    
    def test_preserves_recent_files(self):
        """Test preserves recent files (< 1 hour old).
        
        Requirements: 5.3
        """
        # Create a recent file
        recent_file = self.test_ultra_dl_dir / "recent_file.mp4"
        recent_file.touch()
        
        # Patch the temp_dir path
        with patch('tasks.cleanup_task.Path') as mock_path:
            mock_path.return_value = self.test_ultra_dl_dir
            
            # Import and call the helper
            from tasks.cleanup_task import _cleanup_orphaned_files
            count = _cleanup_orphaned_files()
            
            # Verify recent file was NOT removed
            self.assertTrue(recent_file.exists())
            self.assertEqual(count, 0)
    
    def test_handles_permission_errors_gracefully(self):
        """Test handles permission errors gracefully.
        
        Requirements: 5.3
        """
        # Create an old file
        old_file = self.test_ultra_dl_dir / "protected_file.mp4"
        old_file.touch()
        
        # Set modification time to 2 hours ago
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        os.utime(old_file, (two_hours_ago.timestamp(), two_hours_ago.timestamp()))
        
        # Patch the temp_dir path and unlink to raise OSError
        with patch('tasks.cleanup_task.Path') as mock_path:
            mock_path.return_value = self.test_ultra_dl_dir
            
            with patch.object(Path, 'unlink', side_effect=OSError("Permission denied")):
                with patch('tasks.cleanup_task.logger') as mock_logger:
                    # Import and call the helper
                    from tasks.cleanup_task import _cleanup_orphaned_files
                    
                    # Should not raise exception
                    try:
                        count = _cleanup_orphaned_files()
                    except Exception as e:
                        self.fail(f"_cleanup_orphaned_files should handle OSError gracefully, but raised: {e}")
                    
                    # Verify warning was logged
                    self.assertTrue(mock_logger.warning.called)
    
    def test_returns_correct_count_of_cleaned_items(self):
        """Test returns correct count of cleaned items.
        
        Requirements: 5.3
        """
        # Create multiple old files and directories
        old_file1 = self.test_ultra_dl_dir / "old_file1.mp4"
        old_file1.touch()
        old_file2 = self.test_ultra_dl_dir / "old_file2.mp4"
        old_file2.touch()
        old_dir = self.test_ultra_dl_dir / "old_directory"
        old_dir.mkdir()
        (old_dir / "file.txt").touch()
        
        # Set modification times to 2 hours ago
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        for item in [old_file1, old_file2, old_dir]:
            os.utime(item, (two_hours_ago.timestamp(), two_hours_ago.timestamp()))
        
        # Patch the temp_dir path
        with patch('tasks.cleanup_task.Path') as mock_path:
            mock_path.return_value = self.test_ultra_dl_dir
            
            # Import and call the helper
            from tasks.cleanup_task import _cleanup_orphaned_files
            count = _cleanup_orphaned_files()
            
            # Verify correct count (2 files + 1 directory = 3)
            self.assertEqual(count, 3)


if __name__ == '__main__':
    unittest.main()
