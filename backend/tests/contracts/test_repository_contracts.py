"""
Repository Contract Tests

Shared test suite for repository interfaces that can be run against any implementation.
This ensures all repository implementations (Redis, GCS, SQL, etc.) follow the same contract.

Run with: docker-compose exec backend python test_repository_contracts.py
"""

import os
import sys
import time
from datetime import datetime, timedelta
from typing import Type

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_repository
from domain.job_management.repositories import JobRepository
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobStatus, JobProgress
from domain.file_storage.repositories import FileRepository
from domain.file_storage.entities import DownloadedFile
from infrastructure.redis_job_repository import RedisJobRepository
from infrastructure.redis_file_repository import RedisFileRepository


class JobRepositoryContractTests:
    """
    Contract tests for JobRepository interface.
    
    Any implementation of JobRepository should pass these tests.
    """
    
    def __init__(self, repository: JobRepository, test_prefix: str = "test"):
        self.repo = repository
        self.test_prefix = test_prefix
        self.test_jobs = []
    
    def cleanup(self):
        """Clean up test data."""
        for job_id in self.test_jobs:
            try:
                self.repo.delete(job_id)
            except:
                pass
        self.test_jobs.clear()
    
    def _create_test_job(self, job_id: str = None) -> DownloadJob:
        """Create a test job for testing."""
        if job_id is None:
            job_id = f"{self.test_prefix}_job_{int(time.time() * 1000)}"
        
        now = datetime.utcnow()
        job = DownloadJob(
            job_id=job_id,
            url="https://www.youtube.com/watch?v=test123",
            format_id="137",
            status=JobStatus.PENDING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now
        )
        self.test_jobs.append(job_id)
        return job
    
    def test_save_and_get(self) -> bool:
        """Test basic save and retrieve operations."""
        print("  Testing save and get...")
        
        job = self._create_test_job()
        
        # Save job
        if not self.repo.save(job):
            print("    ✗ Failed to save job")
            return False
        
        # Retrieve job
        retrieved = self.repo.get(job.job_id)
        if retrieved is None:
            print("    ✗ Failed to retrieve saved job")
            return False
        
        # Verify data integrity
        if retrieved.job_id != job.job_id:
            print(f"    ✗ Job ID mismatch: {retrieved.job_id} != {job.job_id}")
            return False
        
        if retrieved.url != job.url:
            print(f"    ✗ URL mismatch: {retrieved.url} != {job.url}")
            return False
        
        if retrieved.status != job.status:
            print(f"    ✗ Status mismatch: {retrieved.status} != {job.status}")
            return False
        
        print("    ✓ Save and get operations successful")
        return True
    
    def test_update_progress(self) -> bool:
        """Test atomic progress updates."""
        print("  Testing update progress...")
        
        job = self._create_test_job()
        self.repo.save(job)
        
        # Start the job first (must be in PROCESSING state to update progress)
        job.start()
        self.repo.save(job)
        
        # Update progress
        progress = JobProgress.downloading(percentage=50, speed="1.5 MB/s", eta=120)
        if not self.repo.update_progress(job.job_id, progress):
            print("    ✗ Failed to update progress")
            return False
        
        # Verify progress was updated
        retrieved = self.repo.get(job.job_id)
        if retrieved is None:
            print("    ✗ Job not found after progress update")
            return False
        
        if retrieved.progress.percentage != 50:
            print(f"    ✗ Progress not updated: {retrieved.progress.percentage} != 50")
            return False
        
        if retrieved.progress.phase != "downloading":
            print(f"    ✗ Progress phase not updated: {retrieved.progress.phase} != downloading")
            return False
        
        print("    ✓ Progress update successful")
        return True
    
    def test_update_status(self) -> bool:
        """Test atomic status updates."""
        print("  Testing update status...")
        
        job = self._create_test_job()
        self.repo.save(job)
        
        # Update status to processing
        if not self.repo.update_status(job.job_id, JobStatus.PROCESSING):
            print("    ✗ Failed to update status to PROCESSING")
            return False
        
        retrieved = self.repo.get(job.job_id)
        if retrieved.status != JobStatus.PROCESSING:
            print(f"    ✗ Status not updated: {retrieved.status} != PROCESSING")
            return False
        
        # Update status to failed with error message
        error_msg = "Test error message"
        if not self.repo.update_status(job.job_id, JobStatus.FAILED, error_msg):
            print("    ✗ Failed to update status to FAILED")
            return False
        
        retrieved = self.repo.get(job.job_id)
        if retrieved.status != JobStatus.FAILED:
            print(f"    ✗ Status not updated to FAILED: {retrieved.status}")
            return False
        
        if retrieved.error_message != error_msg:
            print(f"    ✗ Error message not set: {retrieved.error_message} != {error_msg}")
            return False
        
        print("    ✓ Status update successful")
        return True
    
    def test_delete(self) -> bool:
        """Test delete operation."""
        print("  Testing delete...")
        
        job = self._create_test_job()
        self.repo.save(job)
        
        # Verify job exists
        if not self.repo.exists(job.job_id):
            print("    ✗ Job should exist before deletion")
            return False
        
        # Delete job
        if not self.repo.delete(job.job_id):
            print("    ✗ Failed to delete job")
            return False
        
        # Verify job no longer exists
        if self.repo.exists(job.job_id):
            print("    ✗ Job still exists after deletion")
            return False
        
        # Verify get returns None
        if self.repo.get(job.job_id) is not None:
            print("    ✗ Get should return None for deleted job")
            return False
        
        print("    ✓ Delete operation successful")
        return True
    
    def test_exists(self) -> bool:
        """Test exists check."""
        print("  Testing exists...")
        
        job = self._create_test_job()
        
        # Should not exist before save
        if self.repo.exists(job.job_id):
            print("    ✗ Job should not exist before save")
            return False
        
        # Save job
        self.repo.save(job)
        
        # Should exist after save
        if not self.repo.exists(job.job_id):
            print("    ✗ Job should exist after save")
            return False
        
        print("    ✓ Exists check successful")
        return True
    
    def test_get_nonexistent(self) -> bool:
        """Test retrieving non-existent job."""
        print("  Testing get non-existent job...")
        
        fake_id = f"{self.test_prefix}_nonexistent_{int(time.time() * 1000)}"
        
        result = self.repo.get(fake_id)
        if result is not None:
            print("    ✗ Should return None for non-existent job")
            return False
        
        print("    ✓ Non-existent job handling successful")
        return True
    
    def test_update_nonexistent(self) -> bool:
        """Test updating non-existent job."""
        print("  Testing update non-existent job...")
        
        fake_id = f"{self.test_prefix}_nonexistent_{int(time.time() * 1000)}"
        
        # Update progress should fail gracefully
        progress = JobProgress.downloading(percentage=50, speed="1.5 MB/s")
        result = self.repo.update_progress(fake_id, progress)
        
        if result:
            print("    ✗ Update should fail for non-existent job")
            return False
        
        print("    ✓ Non-existent job update handling successful")
        return True
    
    def test_concurrent_updates(self) -> bool:
        """Test concurrent progress updates."""
        print("  Testing concurrent updates...")
        
        job = self._create_test_job()
        self.repo.save(job)
        
        # Start the job first
        job.start()
        self.repo.save(job)
        
        # Simulate concurrent updates
        for i in range(1, 5):
            progress = JobProgress.downloading(percentage=i * 20, speed=f"{i}.5 MB/s")
            if not self.repo.update_progress(job.job_id, progress):
                print(f"    ✗ Failed to update progress at iteration {i}")
                return False
        
        # Verify final state
        retrieved = self.repo.get(job.job_id)
        if retrieved is None:
            print("    ✗ Job not found after concurrent updates")
            return False
        
        if retrieved.progress.percentage != 80:
            print(f"    ✗ Final progress incorrect: {retrieved.progress.percentage} != 80")
            return False
        
        print("    ✓ Concurrent updates successful")
        return True
    
    def run_all_tests(self) -> bool:
        """Run all contract tests."""
        print("\nJobRepository Contract Tests")
        print("=" * 60)
        
        tests = [
            self.test_save_and_get,
            self.test_update_progress,
            self.test_update_status,
            self.test_delete,
            self.test_exists,
            self.test_get_nonexistent,
            self.test_update_nonexistent,
            self.test_concurrent_updates,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"    ✗ Test failed with exception: {e}")
                results.append(False)
            finally:
                self.cleanup()
        
        passed = sum(results)
        total = len(results)
        print(f"\nJobRepository Tests: {passed}/{total} passed")
        
        return all(results)


class FileRepositoryContractTests:
    """
    Contract tests for FileRepository interface.
    
    Any implementation of FileRepository should pass these tests.
    """
    
    def __init__(self, repository: FileRepository, test_prefix: str = "test"):
        self.repo = repository
        self.test_prefix = test_prefix
        self.test_tokens = []
    
    def cleanup(self):
        """Clean up test data."""
        for token in self.test_tokens:
            try:
                self.repo.delete(token)
            except:
                pass
        self.test_tokens.clear()
    
    def _create_test_file(self, token: str = None, job_id: str = None) -> DownloadedFile:
        """Create a test file for testing."""
        if token is None:
            token = f"{self.test_prefix}_token_{int(time.time() * 1000)}"
        if job_id is None:
            job_id = f"{self.test_prefix}_job_{int(time.time() * 1000)}"
        
        # Create file with 10 minute expiry
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=10)
        
        file = DownloadedFile(
            file_path="/tmp/test_video.mp4",
            token=token,
            job_id=job_id,
            filename="test_video.mp4",
            expires_at=expires_at,
            created_at=now
        )
        self.test_tokens.append(token)
        return file
    
    def test_save_and_get_by_token(self) -> bool:
        """Test save and retrieve by token."""
        print("  Testing save and get by token...")
        
        file = self._create_test_file()
        
        # Save file
        if not self.repo.save(file):
            print("    ✗ Failed to save file")
            return False
        
        # Retrieve by token
        retrieved = self.repo.get_by_token(file.token)
        if retrieved is None:
            print("    ✗ Failed to retrieve saved file")
            return False
        
        # Verify data integrity
        if retrieved.token != file.token:
            print(f"    ✗ Token mismatch: {retrieved.token} != {file.token}")
            return False
        
        if retrieved.job_id != file.job_id:
            print(f"    ✗ Job ID mismatch: {retrieved.job_id} != {file.job_id}")
            return False
        
        if retrieved.filename != file.filename:
            print(f"    ✗ Filename mismatch: {retrieved.filename} != {file.filename}")
            return False
        
        print("    ✓ Save and get by token successful")
        return True
    
    def test_get_by_job_id(self) -> bool:
        """Test retrieve by job ID."""
        print("  Testing get by job ID...")
        
        job_id = f"{self.test_prefix}_job_{int(time.time() * 1000)}"
        file = self._create_test_file(job_id=job_id)
        
        # Save file
        if not self.repo.save(file):
            print("    ✗ Failed to save file")
            return False
        
        # Retrieve by job ID
        retrieved = self.repo.get_by_job_id(job_id)
        if retrieved is None:
            print("    ✗ Failed to retrieve file by job ID")
            return False
        
        if retrieved.token != file.token:
            print(f"    ✗ Token mismatch: {retrieved.token} != {file.token}")
            return False
        
        print("    ✓ Get by job ID successful")
        return True
    
    def test_delete(self) -> bool:
        """Test delete operation."""
        print("  Testing delete...")
        
        file = self._create_test_file()
        self.repo.save(file)
        
        # Verify file exists
        if not self.repo.exists(file.token):
            print("    ✗ File should exist before deletion")
            return False
        
        # Delete file
        if not self.repo.delete(file.token):
            print("    ✗ Failed to delete file")
            return False
        
        # Verify file no longer exists
        if self.repo.exists(file.token):
            print("    ✗ File still exists after deletion")
            return False
        
        # Verify get returns None
        if self.repo.get_by_token(file.token) is not None:
            print("    ✗ Get should return None for deleted file")
            return False
        
        print("    ✓ Delete operation successful")
        return True
    
    def test_exists(self) -> bool:
        """Test exists check."""
        print("  Testing exists...")
        
        file = self._create_test_file()
        
        # Should not exist before save
        if self.repo.exists(file.token):
            print("    ✗ File should not exist before save")
            return False
        
        # Save file
        self.repo.save(file)
        
        # Should exist after save
        if not self.repo.exists(file.token):
            print("    ✗ File should exist after save")
            return False
        
        print("    ✓ Exists check successful")
        return True
    
    def test_get_nonexistent(self) -> bool:
        """Test retrieving non-existent file."""
        print("  Testing get non-existent file...")
        
        fake_token = f"{self.test_prefix}_nonexistent_{int(time.time() * 1000)}"
        
        result = self.repo.get_by_token(fake_token)
        if result is not None:
            print("    ✗ Should return None for non-existent file")
            return False
        
        print("    ✓ Non-existent file handling successful")
        return True
    
    def test_expired_file_handling(self) -> bool:
        """Test handling of expired files."""
        print("  Testing expired file handling...")
        
        # Create file that expires in the past
        token = f"{self.test_prefix}_expired_{int(time.time() * 1000)}"
        job_id = f"{self.test_prefix}_job_{int(time.time() * 1000)}"
        now = datetime.utcnow()
        expires_at = now - timedelta(minutes=1)  # Already expired
        
        file = DownloadedFile(
            file_path="/tmp/expired_video.mp4",
            token=token,
            job_id=job_id,
            filename="expired_video.mp4",
            expires_at=expires_at,
            created_at=now
        )
        self.test_tokens.append(token)
        
        # Try to save expired file (should fail)
        result = self.repo.save(file)
        if result:
            print("    ✗ Should not save expired file")
            # Clean up if it was saved
            self.repo.delete(token)
            return False
        
        print("    ✓ Expired file handling successful")
        return True
    
    def test_multiple_files_same_job(self) -> bool:
        """Test handling multiple files for same job (should overwrite)."""
        print("  Testing multiple files for same job...")
        
        job_id = f"{self.test_prefix}_job_{int(time.time() * 1000)}"
        
        # Create first file
        file1 = self._create_test_file(job_id=job_id)
        self.repo.save(file1)
        
        # Create second file with same job_id
        file2 = self._create_test_file(job_id=job_id)
        self.repo.save(file2)
        
        # Get by job_id should return the latest file
        retrieved = self.repo.get_by_job_id(job_id)
        if retrieved is None:
            print("    ✗ Failed to retrieve file by job ID")
            return False
        
        if retrieved.token != file2.token:
            print(f"    ✗ Should return latest file: {retrieved.token} != {file2.token}")
            return False
        
        print("    ✓ Multiple files for same job handled correctly")
        return True
    
    def run_all_tests(self) -> bool:
        """Run all contract tests."""
        print("\nFileRepository Contract Tests")
        print("=" * 60)
        
        tests = [
            self.test_save_and_get_by_token,
            self.test_get_by_job_id,
            self.test_delete,
            self.test_exists,
            self.test_get_nonexistent,
            self.test_expired_file_handling,
            self.test_multiple_files_same_job,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"    ✗ Test failed with exception: {e}")
                import traceback
                traceback.print_exc()
                results.append(False)
            finally:
                self.cleanup()
        
        passed = sum(results)
        total = len(results)
        print(f"\nFileRepository Tests: {passed}/{total} passed")
        
        return all(results)


def test_redis_implementations():
    """Test Redis implementations against contracts."""
    print("\n" + "=" * 60)
    print("Testing Redis Repository Implementations")
    print("=" * 60)
    
    # Initialize Redis
    init_redis()
    redis_repo = get_redis_repository()
    
    # Test JobRepository implementation
    job_repo = RedisJobRepository(redis_repo)
    job_tests = JobRepositoryContractTests(job_repo, test_prefix="contract_test")
    job_results = job_tests.run_all_tests()
    
    # Test FileRepository implementation
    file_repo = RedisFileRepository(redis_repo)
    file_tests = FileRepositoryContractTests(file_repo, test_prefix="contract_test")
    file_results = file_tests.run_all_tests()
    
    return job_results and file_results


def main():
    """Run all repository contract tests."""
    print("=" * 60)
    print("Repository Contract Test Suite")
    print("=" * 60)
    print("\nThese tests verify that repository implementations")
    print("follow the contract defined by the repository interfaces.")
    print("Any new implementation (GCS, SQL, etc.) should pass these tests.")
    
    try:
        success = test_redis_implementations()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ All repository contract tests passed")
            print("=" * 60)
            return 0
        else:
            print("✗ Some repository contract tests failed")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
