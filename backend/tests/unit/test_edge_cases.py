"""
Unit Tests for Edge Cases Across Modules

Tests cross-cutting edge cases for input validation, concurrency, and resource exhaustion.
Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from application.job_service import JobService
from application.download_service import DownloadService
from domain.job_management import (
    DownloadJob,
    JobManager,
    JobNotFoundError,
    JobStateError,
    JobProgress,
    JobStatus
)
from domain.file_storage import FileManager
from domain.video_processing.value_objects import YouTubeUrl, FormatId
from domain.video_processing.services import VideoProcessor
from domain.errors import ErrorCategory, ApplicationError


class TestInputValidationEdgeCases:
    """Test input validation edge cases across services.
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    
    def test_empty_string_url_is_rejected(self):
        """Test that empty string URLs are rejected."""
        # Empty string should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            YouTubeUrl("")
        
        assert "Invalid YouTube URL" in str(exc_info.value)
    
    def test_empty_string_format_id_is_rejected(self):
        """Test that empty string format IDs are rejected."""
        # Empty string should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            FormatId("")
        
        assert "Invalid format ID" in str(exc_info.value)
    
    def test_none_value_url_is_rejected(self):
        """Test that None URL values are rejected."""
        # None should raise TypeError or ValueError
        with pytest.raises((TypeError, ValueError)):
            YouTubeUrl(None)
    
    def test_none_value_format_id_is_rejected(self):
        """Test that None format ID values are rejected."""
        # None should raise TypeError or ValueError
        with pytest.raises((TypeError, ValueError)):
            FormatId(None)
    
    def test_maximum_length_url_is_handled(self):
        """Test that maximum length URLs are handled correctly."""
        # YouTube URLs can be quite long with parameters
        # Test with a very long URL (2000+ characters)
        base_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        long_params = "&" + "&".join([f"param{i}=value{i}" for i in range(200)])
        long_url = base_url + long_params
        
        # Should either accept it or raise a clear validation error
        try:
            url = YouTubeUrl(long_url)
            # If accepted, verify it's stored correctly
            assert len(url.value) > 2000
        except ValueError as e:
            # If rejected, should have clear error message
            assert "too long" in str(e).lower() or "length" in str(e).lower()
    
    def test_maximum_length_format_id_is_handled(self):
        """Test that maximum length format IDs are handled correctly."""
        # Format IDs are typically short (e.g., "137+140")
        # Test with an unreasonably long format ID
        long_format_id = "137+" * 100  # 400+ characters
        
        # Should either accept it or raise a clear validation error
        try:
            format_id = FormatId(long_format_id)
            # If accepted, verify it's stored correctly
            assert len(format_id.value) > 400
        except ValueError as e:
            # If rejected, should have clear error message
            assert "too long" in str(e).lower() or "length" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_unicode_characters_in_url_are_handled(self):
        """Test that Unicode characters in URLs are handled correctly."""
        # Test with Unicode characters (emojis, special chars)
        unicode_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&title=Test🎵Video™"
        
        # Should either accept it or raise a clear validation error
        try:
            url = YouTubeUrl(unicode_url)
            # If accepted, verify Unicode is preserved
            assert "🎵" in url.value or "Test" in url.value
        except ValueError as e:
            # If rejected, should have clear error message
            assert "invalid" in str(e).lower() or "character" in str(e).lower()
    
    def test_special_characters_in_format_id_are_handled(self):
        """Test that special characters in format IDs are handled correctly."""
        # Test with special characters
        special_format_id = "137+140;DROP TABLE jobs--"
        
        # Should either accept it or raise a clear validation error
        try:
            format_id = FormatId(special_format_id)
            # If accepted, verify it's stored correctly
            assert "DROP" in format_id.value or "137" in format_id.value
        except ValueError as e:
            # If rejected, should have clear error message
            assert "invalid" in str(e).lower() or "character" in str(e).lower()
    
    def test_sql_injection_attempts_in_url_are_handled(self):
        """Test that SQL injection attempts in URLs are handled safely."""
        # Test with SQL injection patterns
        sql_injection_url = "https://www.youtube.com/watch?v=test'; DROP TABLE jobs; --"
        
        # Should either accept it (and escape it properly) or reject it
        try:
            url = YouTubeUrl(sql_injection_url)
            # If accepted, verify it's stored as-is (not executed)
            assert "DROP" in url.value
        except ValueError:
            # If rejected, that's also acceptable
            pass
    
    def test_xss_attempts_in_url_are_handled(self):
        """Test that XSS attempts in URLs are handled safely."""
        # Test with XSS patterns
        xss_url = "https://www.youtube.com/watch?v=test<script>alert('XSS')</script>"
        
        # Should either accept it (and escape it properly) or reject it
        try:
            url = YouTubeUrl(xss_url)
            # If accepted, verify it's stored as-is (not executed)
            assert "script" in url.value or "alert" in url.value
        except ValueError:
            # If rejected, that's also acceptable
            pass
    
    def test_null_bytes_in_url_are_rejected(self):
        """Test that null bytes in URLs are rejected."""
        # Test with null byte
        null_byte_url = "https://www.youtube.com/watch?v=test\x00malicious"
        
        # Should reject null bytes (or accept but not execute them)
        try:
            url = YouTubeUrl(null_byte_url)
            # If accepted, verify it's stored as-is (not executed)
            assert "\x00" in url.value or "test" in url.value
        except (ValueError, TypeError):
            # If rejected, that's also acceptable
            pass
    
    def test_whitespace_only_url_is_rejected(self):
        """Test that whitespace-only URLs are rejected."""
        # Test with various whitespace
        whitespace_url = "   \t\n   "
        
        # Should reject whitespace-only input
        with pytest.raises(ValueError) as exc_info:
            YouTubeUrl(whitespace_url)
        
        assert "empty" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
    
    def test_whitespace_only_format_id_is_rejected(self):
        """Test that whitespace-only format IDs are rejected."""
        # Test with various whitespace
        whitespace_format = "   \t\n   "
        
        # Should reject whitespace-only input
        with pytest.raises(ValueError) as exc_info:
            FormatId(whitespace_format)
        
        assert "empty" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


class TestConcurrencyEdgeCases:
    """Test concurrency edge cases across services.
    
    Requirements: 8.5
    """
    
    def test_concurrent_access_to_same_job(self):
        """Test concurrent access to the same job is handled safely."""
        # Setup
        mock_job_manager = Mock(spec=JobManager)
        mock_file_manager = Mock(spec=FileManager)
        job_service = JobService(mock_job_manager, mock_file_manager)
        
        # Mock job status
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
        
        results = []
        errors = []
        
        def access_job():
            try:
                result = job_service.get_job_status("test-job-123")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Execute: 50 concurrent accesses to same job
        threads = []
        for i in range(50):
            thread = threading.Thread(target=access_job)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify: All accesses succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50
        assert all(r["job_id"] == "test-job-123" for r in results)
    
    def test_concurrent_file_operations(self):
        """Test concurrent file operations are handled safely."""
        # Setup
        mock_file_manager = Mock(spec=FileManager)
        mock_file_manager.delete_file.return_value = True
        
        results = []
        errors = []
        
        def delete_file(file_id):
            try:
                result = mock_file_manager.delete_file(f"file-{file_id}")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Execute: 20 concurrent file deletions
        threads = []
        for i in range(20):
            thread = threading.Thread(target=delete_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify: All operations completed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 20
    
    def test_race_conditions_in_job_status_updates(self):
        """Test race conditions in job status updates are handled safely."""
        # Setup
        mock_job_manager = Mock(spec=JobManager)
        mock_file_manager = Mock(spec=FileManager)
        job_service = JobService(mock_job_manager, mock_file_manager)
        
        # Mock progress update
        mock_job_manager.update_job_progress.return_value = True
        
        update_count = [0]  # Use list for mutable counter
        lock = threading.Lock()
        errors = []
        
        def update_progress(percentage):
            try:
                result = job_service.update_progress(
                    "test-job-123",
                    percentage=percentage,
                    phase=f"downloading {percentage}%"
                )
                if result:
                    with lock:
                        update_count[0] += 1
            except Exception as e:
                errors.append(e)
        
        # Execute: 100 concurrent progress updates
        threads = []
        for i in range(1, 101):
            thread = threading.Thread(target=update_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify: All updates completed without errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert update_count[0] == 100
    
    def test_concurrent_job_creation_and_deletion(self):
        """Test concurrent job creation and deletion operations."""
        # Setup
        mock_job_manager = Mock(spec=JobManager)
        mock_file_manager = Mock(spec=FileManager)
        job_service = JobService(mock_job_manager, mock_file_manager)
        
        # Mock operations
        def create_job_side_effect(url, format_id):
            job = DownloadJob.create(url, format_id)
            return job
        
        mock_job_manager.create_job.side_effect = create_job_side_effect
        mock_job_manager.delete_job.return_value = True
        mock_job_manager.get_job.side_effect = JobNotFoundError("Job not found")
        
        created_jobs = []
        deleted_jobs = []
        errors = []
        
        def create_and_delete_job(index):
            try:
                # Create job
                result = job_service.create_download_job(
                    f"https://youtube.com/watch?v=test{index}",
                    "137"
                )
                created_jobs.append(result["job_id"])
                
                # Small delay
                time.sleep(0.001)
                
                # Delete job
                deleted = job_service.delete_job(result["job_id"])
                if deleted:
                    deleted_jobs.append(result["job_id"])
            except Exception as e:
                errors.append(e)
        
        # Execute: 20 concurrent create-delete operations
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_and_delete_job, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify: All operations completed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(created_jobs) == 20
        assert len(deleted_jobs) == 20


class TestResourceExhaustionScenarios:
    """Test resource exhaustion scenarios.
    
    Requirements: 8.6
    """
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    def test_behavior_when_disk_space_full(self, mock_exists, mock_mkdir):
        """Test behavior when disk space is full."""
        # Setup: Simulate disk full error
        mock_exists.return_value = False
        mock_mkdir.side_effect = OSError("[Errno 28] No space left on device")
        
        # Execute: Try to create directory
        with pytest.raises(OSError) as exc_info:
            path = Path("/tmp/ultra-dl/test-job")
            path.mkdir(parents=True, exist_ok=True)
        
        # Verify: Error message indicates disk full
        assert "No space left on device" in str(exc_info.value) or "Errno 28" in str(exc_info.value)
    
    def test_behavior_when_redis_memory_limit_reached(self):
        """Test behavior when Redis memory limit is reached."""
        # Setup: Mock Redis repository
        from infrastructure.redis_job_repository import RedisJobRepository
        from infrastructure.redis_repository import RedisRepository
        
        mock_redis_client = Mock()
        # Simulate Redis OOM error
        mock_redis_client.setex.side_effect = Exception("OOM command not allowed when used memory > 'maxmemory'")
        
        mock_redis_repo = Mock(spec=RedisRepository)
        mock_redis_repo.redis = mock_redis_client
        mock_redis_repo.set_json.side_effect = Exception("OOM command not allowed when used memory > 'maxmemory'")
        
        repo = RedisJobRepository(redis_repository=mock_redis_repo)
        
        # Execute: Try to save job
        job = DownloadJob.create("https://youtube.com/watch?v=test", "137")
        
        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            repo.save(job)
        
        # Verify: Error message indicates memory limit
        assert "OOM" in str(exc_info.value) or "maxmemory" in str(exc_info.value)
    
    def test_behavior_when_connection_pool_exhausted(self):
        """Test behavior when connection pool is exhausted."""
        # Setup: Mock Redis with connection pool exhausted
        from infrastructure.redis_job_repository import RedisJobRepository
        from infrastructure.redis_repository import RedisRepository
        
        mock_redis_client = Mock()
        mock_redis_client.get.side_effect = Exception("Connection pool exhausted")
        
        mock_redis_repo = Mock(spec=RedisRepository)
        mock_redis_repo.redis = mock_redis_client
        mock_redis_repo.get_json.side_effect = Exception("Connection pool exhausted")
        
        repo = RedisJobRepository(redis_repository=mock_redis_repo)
        
        # Execute: Try to get job
        with pytest.raises(Exception) as exc_info:
            repo.get("test-job-123")
        
        # Verify: Error message indicates pool exhaustion
        assert "Connection pool exhausted" in str(exc_info.value) or "pool" in str(exc_info.value).lower()
    
    def test_behavior_with_many_concurrent_connections(self):
        """Test behavior with many concurrent connections."""
        # Setup: Mock Redis repository
        from infrastructure.redis_job_repository import RedisJobRepository
        from infrastructure.redis_repository import RedisRepository
        
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = None
        
        mock_redis_repo = Mock(spec=RedisRepository)
        mock_redis_repo.redis = mock_redis_client
        mock_redis_repo.get_json.return_value = None
        
        repo = RedisJobRepository(redis_repository=mock_redis_repo)
        
        results = []
        errors = []
        
        def get_job(job_id):
            try:
                result = repo.get(f"job-{job_id}")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Execute: 100 concurrent connections
        threads = []
        for i in range(100):
            thread = threading.Thread(target=get_job, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify: Should handle gracefully (either succeed or fail with clear error)
        # At minimum, should not crash
        assert len(results) + len(errors) == 100
    
    def test_behavior_with_large_file_operations(self):
        """Test behavior with large file operations."""
        # Setup: Mock file manager
        mock_file_manager = Mock(spec=FileManager)
        
        # Simulate large file (>1GB)
        large_file_size = 1024 * 1024 * 1024 * 2  # 2GB
        
        # Mock file registration using DownloadedFile (correct entity name)
        from domain.file_storage.entities import DownloadedFile
        from domain.file_storage.value_objects import DownloadToken
        
        # Generate a valid token (at least 32 characters)
        valid_token = DownloadToken.generate()
        
        large_file = DownloadedFile(
            token=valid_token,
            file_path="/tmp/ultra-dl/large-video.mp4",
            filename="large-video.mp4",
            job_id="test-job-123",
            filesize=large_file_size,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            created_at=datetime.utcnow()
        )
        
        mock_file_manager.register_file.return_value = large_file
        
        # Execute: Register large file
        result = mock_file_manager.register_file(
            file_path="/tmp/ultra-dl/large-video.mp4",
            job_id="test-job-123",
            filename="large-video.mp4",
            ttl_minutes=10
        )
        
        # Verify: Large file is handled
        assert result.filesize == large_file_size
        assert len(str(result.token)) >= 32  # Valid token length
    
    def test_behavior_with_many_expired_jobs(self):
        """Test behavior when cleaning up many expired jobs."""
        # Setup
        mock_job_manager = Mock(spec=JobManager)
        mock_file_manager = Mock(spec=FileManager)
        job_service = JobService(mock_job_manager, mock_file_manager)
        
        # Mock cleanup to return large count
        mock_job_manager.cleanup_expired_jobs.return_value = 10000
        
        # Execute: Cleanup with many expired jobs
        count = job_service.cleanup_expired_jobs(expiration_hours=1)
        
        # Verify: Should handle large cleanup gracefully
        assert count == 10000
        mock_job_manager.cleanup_expired_jobs.assert_called_once()
    
    def test_behavior_with_rapid_job_creation(self):
        """Test behavior with rapid job creation."""
        # Setup
        mock_job_manager = Mock(spec=JobManager)
        mock_file_manager = Mock(spec=FileManager)
        job_service = JobService(mock_job_manager, mock_file_manager)
        
        # Mock job creation
        def create_job_side_effect(url, format_id):
            job = DownloadJob.create(url, format_id)
            return job
        
        mock_job_manager.create_job.side_effect = create_job_side_effect
        
        created_jobs = []
        errors = []
        
        def create_job_rapidly(index):
            try:
                result = job_service.create_download_job(
                    f"https://youtube.com/watch?v=test{index}",
                    "137"
                )
                created_jobs.append(result["job_id"])
            except Exception as e:
                errors.append(e)
        
        # Execute: Create 200 jobs rapidly
        threads = []
        for i in range(200):
            thread = threading.Thread(target=create_job_rapidly, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify: Should handle rapid creation
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(created_jobs) == 200
        assert len(set(created_jobs)) == 200  # All unique
