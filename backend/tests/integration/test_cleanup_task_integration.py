"""
Integration Tests for Cleanup Task

Tests the cleanup_expired_jobs Celery task with real Flask app context,
Redis, and filesystem operations. Verifies end-to-end cleanup workflow.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.6
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from flask import Flask

from app_factory import create_app
from domain.file_storage.entities import DownloadedFile
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobStatus
from infrastructure.redis_file_repository import RedisFileRepository
from infrastructure.redis_job_repository import RedisJobRepository
from tasks.cleanup_task import cleanup_expired_jobs


class TestCleanupTaskIntegration(unittest.TestCase):
    """Integration tests with real Flask app context and services."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Create real Flask app with all services
        self.app = create_app()
        
        # Create temporary storage directory
        self.temp_storage = tempfile.mkdtemp()
        
        # Get repositories from container
        with self.app.app_context():
            self.job_repo = self.app.container.resolve(RedisJobRepository)
            self.file_repo = self.app.container.resolve(RedisFileRepository)
        
        # Clean up Redis before each test
        self._cleanup_redis()
    
    def tearDown(self):
        """Clean up test fixtures after each test."""
        # Clean up Redis
        self._cleanup_redis()
        
        # Remove temporary storage
        if os.path.exists(self.temp_storage):
            shutil.rmtree(self.temp_storage)
    
    def _cleanup_redis(self):
        """Clean up Redis test data."""
        with self.app.app_context():
            # Get all job keys and delete them
            redis_client = self.job_repo.redis_repo.redis
            job_keys = redis_client.keys("job:*")
            if job_keys:
                redis_client.delete(*job_keys)
            
            # Get all file keys and delete them
            file_keys = redis_client.keys("file_token:*")
            if file_keys:
                redis_client.delete(*file_keys)
            
            file_job_keys = redis_client.keys("file_job:*")
            if file_job_keys:
                redis_client.delete(*file_job_keys)
    
    def test_cleanup_removes_expired_jobs_from_redis(self):
        """
        Test cleanup removes expired jobs from Redis.
        
        Creates expired and non-expired jobs, runs cleanup task,
        and verifies only expired jobs are removed.
        
        Requirements: 5.2, 5.4
        """
        print("\n=== Testing Cleanup Removes Expired Jobs from Redis ===")
        
        with self.app.app_context():
            # Create expired job (created 2 hours ago, in terminal state)
            expired_job = DownloadJob.create(
                "https://youtube.com/watch?v=expired",
                "137+140"
            )
            expired_job.job_id = "job-expired"
            expired_job.status = JobStatus.COMPLETED  # Must be in terminal state
            expired_job.created_at = datetime.utcnow() - timedelta(hours=2)
            expired_job.updated_at = datetime.utcnow() - timedelta(hours=2)
            self.job_repo.save(expired_job)
            
            # Create recent job (created 10 minutes ago)
            recent_job = DownloadJob.create(
                "https://youtube.com/watch?v=recent",
                "137+140"
            )
            recent_job.job_id = "job-recent"
            recent_job.created_at = datetime.utcnow() - timedelta(minutes=10)
            recent_job.updated_at = datetime.utcnow() - timedelta(minutes=10)
            self.job_repo.save(recent_job)
            
            # Verify both jobs exist
            self.assertIsNotNone(self.job_repo.get("job-expired"))
            self.assertIsNotNone(self.job_repo.get("job-recent"))
            
            # Run cleanup task
            result = cleanup_expired_jobs()
            
            # Verify expired job was removed
            self.assertIsNone(self.job_repo.get("job-expired"))
            
            # Verify recent job still exists
            self.assertIsNotNone(self.job_repo.get("job-recent"))
            
            # Verify statistics
            self.assertGreaterEqual(result['expired_jobs_removed'], 1)
            
            print(f"✓ Cleanup removed {result['expired_jobs_removed']} expired job(s)")
    
    def test_cleanup_removes_expired_files_from_filesystem(self):
        """
        Test cleanup removes expired files from filesystem.
        
        Creates expired and non-expired files, runs cleanup task,
        and verifies only expired files are removed.
        
        Requirements: 5.2, 5.3
        """
        print("\n=== Testing Cleanup Removes Expired Files from Filesystem ===")
        
        with self.app.app_context():
            # Create expired file (created 2 hours ago)
            expired_file_path = os.path.join(self.temp_storage, "expired_video.mp4")
            with open(expired_file_path, 'w') as f:
                f.write("expired video content")
            
            # Create expired file - use create method then manually override expiration
            # This ensures we have a valid token and the file gets saved to Redis
            expired_file = DownloadedFile.create(
                file_path=expired_file_path,
                job_id="job-expired",
                filename="expired_video.mp4",
                ttl_minutes=120  # Use future TTL so Redis accepts it
            )
            # Override the expiration to make it expired for our cleanup logic
            expired_file.expires_at = datetime.utcnow() - timedelta(hours=1)
            expired_file.created_at = datetime.utcnow() - timedelta(hours=2)
            # Save to Redis (will be saved with TTL based on current expires_at calculation)
            # We need to save it directly to Redis with custom TTL
            redis_client = self.file_repo.redis_repo.redis
            token_key = f"file_token:{expired_file.token}"
            job_key = f"file_job:{expired_file.job_id}"
            redis_client.setex(token_key, 7200, json.dumps(expired_file.to_dict()))  # 2 hour TTL in Redis
            redis_client.setex(job_key, 7200, json.dumps({"token": str(expired_file.token)}))
            
            # Create recent file (created 10 minutes ago)
            recent_file_path = os.path.join(self.temp_storage, "recent_video.mp4")
            with open(recent_file_path, 'w') as f:
                f.write("recent video content")
            
            # Create recent file (not expired)
            recent_file = DownloadedFile.create(
                file_path=recent_file_path,
                job_id="job-recent",
                filename="recent_video.mp4",
                ttl_minutes=15  # Not expired
            )
            self.file_repo.save(recent_file)
            
            # Verify both files exist in filesystem
            self.assertTrue(os.path.exists(expired_file_path))
            self.assertTrue(os.path.exists(recent_file_path))
            
            # Verify both files exist in Redis
            self.assertIsNotNone(self.file_repo.get_by_job_id("job-expired"))
            self.assertIsNotNone(self.file_repo.get_by_job_id("job-recent"))
            
            # Run cleanup task
            result = cleanup_expired_jobs()
            
            # Verify expired file was removed from filesystem
            self.assertFalse(os.path.exists(expired_file_path))
            
            # Verify recent file still exists in filesystem
            self.assertTrue(os.path.exists(recent_file_path))
            
            # Verify expired file was removed from Redis
            self.assertIsNone(self.file_repo.get_by_job_id("job-expired"))
            
            # Verify recent file still exists in Redis
            self.assertIsNotNone(self.file_repo.get_by_job_id("job-recent"))
            
            # Verify statistics
            self.assertGreaterEqual(result['expired_files_removed'], 1)
            
            print(f"✓ Cleanup removed {result['expired_files_removed']} expired file(s)")
    
    def test_cleanup_logs_statistics_correctly(self):
        """
        Test cleanup logs statistics correctly.
        
        Creates test data, runs cleanup task, and verifies
        statistics are logged with correct values.
        
        Requirements: 5.6
        """
        print("\n=== Testing Cleanup Logs Statistics Correctly ===")
        
        with self.app.app_context():
            # Create expired job (in terminal state)
            expired_job = DownloadJob.create(
                "https://youtube.com/watch?v=test",
                "137+140"
            )
            expired_job.job_id = "job-test"
            expired_job.status = JobStatus.COMPLETED  # Must be in terminal state
            expired_job.created_at = datetime.utcnow() - timedelta(hours=2)
            expired_job.updated_at = datetime.utcnow() - timedelta(hours=2)
            self.job_repo.save(expired_job)
            
            # Create expired file
            expired_file_path = os.path.join(self.temp_storage, "test_video.mp4")
            with open(expired_file_path, 'w') as f:
                f.write("test video content")
            
            # Create expired file
            expired_file = DownloadedFile.create(
                file_path=expired_file_path,
                job_id="job-test",
                filename="test_video.mp4",
                ttl_minutes=120
            )
            expired_file.expires_at = datetime.utcnow() - timedelta(hours=1)
            expired_file.created_at = datetime.utcnow() - timedelta(hours=2)
            # Save directly to Redis with custom TTL
            redis_client = self.file_repo.redis_repo.redis
            token_key = f"file_token:{expired_file.token}"
            job_key = f"file_job:{expired_file.job_id}"
            redis_client.setex(token_key, 7200, json.dumps(expired_file.to_dict()))
            redis_client.setex(job_key, 7200, json.dumps({"token": str(expired_file.token)}))
            
            # Run cleanup task with logging capture
            with patch('tasks.cleanup_task.logger') as mock_logger:
                result = cleanup_expired_jobs()
                
                # Verify logging was called
                self.assertTrue(mock_logger.info.called)
                
                # Verify cleanup summary was logged
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                summary_logged = any('Cleanup completed' in str(call) for call in log_calls)
                self.assertTrue(summary_logged, "Cleanup summary should be logged")
                
                # Verify statistics in result
                self.assertIsInstance(result, dict)
                self.assertIn('expired_jobs_removed', result)
                self.assertIn('expired_files_removed', result)
                self.assertIn('orphaned_files_cleaned', result)
                self.assertIn('errors', result)
                
                # Verify counts are reasonable
                self.assertGreaterEqual(result['expired_jobs_removed'], 0)
                self.assertGreaterEqual(result['expired_files_removed'], 0)
                self.assertGreaterEqual(result['orphaned_files_cleaned'], 0)
                self.assertIsInstance(result['errors'], list)
                
                print(f"✓ Cleanup logged statistics: {result}")
    
    def test_cleanup_handles_missing_app_context_gracefully(self):
        """
        Test cleanup handles missing app context gracefully.
        
        Simulates an error during cleanup and verifies
        it handles the error gracefully without crashing.
        
        Requirements: 5.6
        """
        print("\n=== Testing Cleanup Handles Missing App Context Gracefully ===")
        
        with self.app.app_context():
            # Mock container.resolve to raise RuntimeError (simulating app context issue)
            with patch.object(self.app.container, 'resolve') as mock_resolve:
                mock_resolve.side_effect = RuntimeError("Working outside of application context")
                
                # Run cleanup task - should not crash
                try:
                    result = cleanup_expired_jobs()
                    
                    # Verify task returned error result
                    self.assertIsInstance(result, dict)
                    self.assertGreater(len(result['errors']), 0)
                    self.assertTrue(any('Cleanup task failed' in err for err in result['errors']))
                    
                    print("✓ Cleanup handled app context error gracefully")
                    
                except Exception as e:
                    self.fail(f"Cleanup task should handle errors gracefully, but raised: {e}")
    
    def test_cleanup_with_multiple_expired_items(self):
        """
        Test cleanup with multiple expired jobs and files.
        
        Creates multiple expired items, runs cleanup task,
        and verifies all are removed correctly.
        
        Requirements: 5.2, 5.3, 5.4
        """
        print("\n=== Testing Cleanup with Multiple Expired Items ===")
        
        with self.app.app_context():
            # Create multiple expired jobs (in terminal state)
            for i in range(3):
                job = DownloadJob.create(
                    f"https://youtube.com/watch?v=test{i}",
                    "137+140"
                )
                job.job_id = f"job-expired-{i}"
                job.status = JobStatus.COMPLETED  # Must be in terminal state
                job.created_at = datetime.utcnow() - timedelta(hours=2)
                job.updated_at = datetime.utcnow() - timedelta(hours=2)
                self.job_repo.save(job)
            
            # Create multiple expired files
            redis_client = self.file_repo.redis_repo.redis
            for i in range(3):
                file_path = os.path.join(self.temp_storage, f"expired_video_{i}.mp4")
                with open(file_path, 'w') as f:
                    f.write(f"expired video content {i}")
                
                file = DownloadedFile.create(
                    file_path=file_path,
                    job_id=f"job-expired-{i}",
                    filename=f"expired_video_{i}.mp4",
                    ttl_minutes=120
                )
                file.expires_at = datetime.utcnow() - timedelta(hours=1)
                file.created_at = datetime.utcnow() - timedelta(hours=2)
                # Save directly to Redis with custom TTL
                token_key = f"file_token:{file.token}"
                job_key = f"file_job:{file.job_id}"
                redis_client.setex(token_key, 7200, json.dumps(file.to_dict()))
                redis_client.setex(job_key, 7200, json.dumps({"token": str(file.token)}))
            
            # Verify all items exist
            for i in range(3):
                self.assertIsNotNone(self.job_repo.get(f"job-expired-{i}"))
                self.assertIsNotNone(self.file_repo.get_by_job_id(f"job-expired-{i}"))
                self.assertTrue(os.path.exists(os.path.join(self.temp_storage, f"expired_video_{i}.mp4")))
            
            # Run cleanup task
            result = cleanup_expired_jobs()
            
            # Verify all expired items were removed
            for i in range(3):
                self.assertIsNone(self.job_repo.get(f"job-expired-{i}"))
                self.assertIsNone(self.file_repo.get_by_job_id(f"job-expired-{i}"))
                self.assertFalse(os.path.exists(os.path.join(self.temp_storage, f"expired_video_{i}.mp4")))
            
            # Verify statistics
            self.assertGreaterEqual(result['expired_jobs_removed'], 3)
            self.assertGreaterEqual(result['expired_files_removed'], 3)
            
            print(f"✓ Cleanup removed {result['expired_jobs_removed']} jobs and {result['expired_files_removed']} files")
    
    def test_cleanup_preserves_non_expired_items(self):
        """
        Test cleanup preserves non-expired items.
        
        Creates mix of expired and non-expired items, runs cleanup,
        and verifies only expired items are removed.
        
        Requirements: 5.2, 5.3, 5.4
        """
        print("\n=== Testing Cleanup Preserves Non-Expired Items ===")
        
        with self.app.app_context():
            # Create expired job (in terminal state)
            expired_job = DownloadJob.create(
                "https://youtube.com/watch?v=expired",
                "137+140"
            )
            expired_job.job_id = "job-expired"
            expired_job.status = JobStatus.COMPLETED  # Must be in terminal state
            expired_job.created_at = datetime.utcnow() - timedelta(hours=2)
            expired_job.updated_at = datetime.utcnow() - timedelta(hours=2)
            self.job_repo.save(expired_job)
            
            # Create non-expired jobs with different statuses
            pending_job = DownloadJob.create(
                "https://youtube.com/watch?v=pending",
                "137+140"
            )
            pending_job.job_id = "job-pending"
            pending_job.status = JobStatus.PENDING
            self.job_repo.save(pending_job)
            
            processing_job = DownloadJob.create(
                "https://youtube.com/watch?v=processing",
                "137+140"
            )
            processing_job.job_id = "job-processing"
            processing_job.status = JobStatus.PROCESSING
            self.job_repo.save(processing_job)
            
            completed_job = DownloadJob.create(
                "https://youtube.com/watch?v=completed",
                "137+140"
            )
            completed_job.job_id = "job-completed"
            completed_job.status = JobStatus.COMPLETED
            completed_job.created_at = datetime.utcnow() - timedelta(minutes=30)
            completed_job.updated_at = datetime.utcnow() - timedelta(minutes=30)
            self.job_repo.save(completed_job)
            
            # Run cleanup task
            result = cleanup_expired_jobs()
            
            # Verify expired job was removed
            self.assertIsNone(self.job_repo.get("job-expired"))
            
            # Verify non-expired jobs still exist
            self.assertIsNotNone(self.job_repo.get("job-pending"))
            self.assertIsNotNone(self.job_repo.get("job-processing"))
            self.assertIsNotNone(self.job_repo.get("job-completed"))
            
            print("✓ Cleanup preserved non-expired items")
    
    def test_cleanup_handles_partial_failures(self):
        """
        Test cleanup handles partial failures gracefully.
        
        Simulates failure in one cleanup operation and verifies
        other operations still complete successfully.
        
        Requirements: 5.5, 5.6
        """
        print("\n=== Testing Cleanup Handles Partial Failures ===")
        
        with self.app.app_context():
            # Create expired job (in terminal state)
            expired_job = DownloadJob.create(
                "https://youtube.com/watch?v=test",
                "137+140"
            )
            expired_job.job_id = "job-test"
            expired_job.status = JobStatus.COMPLETED  # Must be in terminal state
            expired_job.created_at = datetime.utcnow() - timedelta(hours=2)
            expired_job.updated_at = datetime.utcnow() - timedelta(hours=2)
            self.job_repo.save(expired_job)
            
            # Mock file cleanup to raise exception
            with patch('tasks.cleanup_task.get_file_manager') as mock_get_file_manager:
                mock_file_manager = Mock()
                mock_file_manager.file_repo.get_expired_files.side_effect = Exception("File cleanup error")
                mock_get_file_manager.return_value = mock_file_manager
                
                # Run cleanup task
                result = cleanup_expired_jobs()
                
                # Verify task didn't crash
                self.assertIsInstance(result, dict)
                
                # Verify error was recorded
                self.assertGreater(len(result['errors']), 0)
                self.assertTrue(any('Error cleaning up expired files' in err for err in result['errors']))
                
                # Verify job cleanup still ran (check if job was removed)
                # Note: Job cleanup should still work even if file cleanup failed
                self.assertIsNone(self.job_repo.get("job-test"))
                self.assertGreaterEqual(result['expired_jobs_removed'], 1)
                
                print("✓ Cleanup handled partial failure gracefully")


def run_all_tests():
    """Run all cleanup task integration tests."""
    print("\n" + "=" * 60)
    print("CLEANUP TASK INTEGRATION TESTS")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCleanupTaskIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
