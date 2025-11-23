"""
Domain unit tests for core business logic.

Tests DownloadJob entity, JobManager service, and FileManager service.
"""

import sys
import time
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from domain.job_management.entities import DownloadJob
from domain.job_management.services import JobManager, JobNotFoundError, JobStateError
from domain.job_management.value_objects import JobStatus, JobProgress
from domain.file_storage.entities import DownloadedFile
from domain.file_storage.services import FileManager, FileNotFoundError as FileNotFoundError2, FileExpiredError
from domain.events import JobStartedEvent, JobCompletedEvent, JobFailedEvent, JobProgressUpdatedEvent


# Mock Repositories
class MockJobRepository:
    """Mock implementation of JobRepository for testing."""
    
    def __init__(self):
        self.jobs = {}
        self.save_should_fail = False
    
    def save(self, job: DownloadJob) -> bool:
        if self.save_should_fail:
            return False
        self.jobs[job.job_id] = job
        return True
    
    def get(self, job_id: str):
        return self.jobs.get(job_id)
    
    def delete(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False
    
    def update_progress(self, job_id: str, progress: JobProgress) -> bool:
        if job_id in self.jobs:
            self.jobs[job_id].progress = progress
            self.jobs[job_id].updated_at = datetime.utcnow()
            return True
        return False
    
    def exists(self, job_id: str) -> bool:
        return job_id in self.jobs
    
    def get_expired_jobs(self, expiration_time: timedelta):
        cutoff = datetime.utcnow() - expiration_time
        return [
            job_id for job_id, job in self.jobs.items()
            if job.updated_at < cutoff and job.is_terminal()
        ]


class MockFileRepository:
    """Mock implementation of FileRepository for testing."""
    
    def __init__(self):
        self.files_by_token = {}
        self.files_by_job = {}
        self.save_should_fail = False
    
    def save(self, file: DownloadedFile) -> bool:
        if self.save_should_fail:
            return False
        self.files_by_token[str(file.token)] = file
        self.files_by_job[file.job_id] = file
        return True
    
    def get_by_token(self, token: str):
        return self.files_by_token.get(token)
    
    def get_by_job_id(self, job_id: str):
        return self.files_by_job.get(job_id)
    
    def delete(self, token: str) -> bool:
        if token in self.files_by_token:
            file = self.files_by_token[token]
            del self.files_by_token[token]
            if file.job_id in self.files_by_job:
                del self.files_by_job[file.job_id]
            return True
        return False
    
    def get_expired_files(self):
        return [
            file for file in self.files_by_token.values()
            if file.is_expired()
        ]
    
    def exists(self, token: str) -> bool:
        return token in self.files_by_token


class MockFileStorageRepository:
    """Mock implementation of FileStorageRepository for testing."""
    
    def __init__(self):
        self.deleted_files = []
        self.saved_files = []
        self.existing_files = set()
        self.file_sizes = {}
    
    def save_file(self, source_path: str, destination_path: str) -> bool:
        self.saved_files.append((source_path, destination_path))
        self.existing_files.add(destination_path)
        return True
    
    def delete_file(self, path: str) -> bool:
        self.deleted_files.append(path)
        if path in self.existing_files:
            self.existing_files.remove(path)
        return True
    
    def file_exists(self, path: str) -> bool:
        return path in self.existing_files or os.path.exists(path)
    
    def get_file_size(self, path: str):
        if path in self.file_sizes:
            return self.file_sizes[path]
        if os.path.exists(path):
            return os.path.getsize(path)
        return None


# Test Domain Events
def test_domain_events():
    """Test domain event creation, serialization, and immutability."""
    print("\n=== Testing Domain Events ===")
    
    # Test 1: JobStartedEvent creation
    print("\n1. Testing JobStartedEvent creation...")
    now = datetime.utcnow()
    started_event = JobStartedEvent(
        aggregate_id="job-123",
        occurred_at=now,
        url="https://youtube.com/watch?v=test",
        format_id="137"
    )
    assert started_event.aggregate_id == "job-123", "Aggregate ID should match"
    assert started_event.occurred_at == now, "Occurred at should match"
    assert started_event.url == "https://youtube.com/watch?v=test", "URL should match"
    assert started_event.format_id == "137", "Format ID should match"
    print("   ✓ JobStartedEvent creation successful")
    
    # Test 2: JobStartedEvent serialization
    print("\n2. Testing JobStartedEvent serialization...")
    event_dict = started_event.to_dict()
    assert event_dict["event_type"] == "JobStartedEvent", "Event type should be correct"
    assert event_dict["aggregate_id"] == "job-123", "Aggregate ID should be serialized"
    assert event_dict["url"] == "https://youtube.com/watch?v=test", "URL should be serialized"
    assert event_dict["format_id"] == "137", "Format ID should be serialized"
    assert "occurred_at" in event_dict, "Occurred at should be serialized"
    print("   ✓ JobStartedEvent serialization successful")
    
    # Test 3: JobCompletedEvent creation
    print("\n3. Testing JobCompletedEvent creation...")
    expire_at = datetime.utcnow() + timedelta(minutes=10)
    completed_event = JobCompletedEvent(
        aggregate_id="job-123",
        occurred_at=now,
        download_url="http://example.com/download",
        expire_at=expire_at
    )
    assert completed_event.aggregate_id == "job-123", "Aggregate ID should match"
    assert completed_event.download_url == "http://example.com/download", "Download URL should match"
    assert completed_event.expire_at == expire_at, "Expire at should match"
    print("   ✓ JobCompletedEvent creation successful")
    
    # Test 4: JobCompletedEvent serialization
    print("\n4. Testing JobCompletedEvent serialization...")
    event_dict = completed_event.to_dict()
    assert event_dict["event_type"] == "JobCompletedEvent", "Event type should be correct"
    assert event_dict["download_url"] == "http://example.com/download", "Download URL should be serialized"
    assert "expire_at" in event_dict, "Expire at should be serialized"
    print("   ✓ JobCompletedEvent serialization successful")
    
    # Test 5: JobFailedEvent creation
    print("\n5. Testing JobFailedEvent creation...")
    failed_event = JobFailedEvent(
        aggregate_id="job-123",
        occurred_at=now,
        error_message="Download failed",
        error_category="DOWNLOAD_ERROR"
    )
    assert failed_event.aggregate_id == "job-123", "Aggregate ID should match"
    assert failed_event.error_message == "Download failed", "Error message should match"
    assert failed_event.error_category == "DOWNLOAD_ERROR", "Error category should match"
    print("   ✓ JobFailedEvent creation successful")
    
    # Test 6: JobFailedEvent serialization
    print("\n6. Testing JobFailedEvent serialization...")
    event_dict = failed_event.to_dict()
    assert event_dict["event_type"] == "JobFailedEvent", "Event type should be correct"
    assert event_dict["error_message"] == "Download failed", "Error message should be serialized"
    assert event_dict["error_category"] == "DOWNLOAD_ERROR", "Error category should be serialized"
    print("   ✓ JobFailedEvent serialization successful")
    
    # Test 7: JobProgressUpdatedEvent creation
    print("\n7. Testing JobProgressUpdatedEvent creation...")
    progress = JobProgress.downloading(50, speed="2 MB/s", eta=60)
    progress_event = JobProgressUpdatedEvent(
        aggregate_id="job-123",
        occurred_at=now,
        progress=progress
    )
    assert progress_event.aggregate_id == "job-123", "Aggregate ID should match"
    assert progress_event.progress.percentage == 50, "Progress percentage should match"
    assert progress_event.progress.speed == "2 MB/s", "Progress speed should match"
    print("   ✓ JobProgressUpdatedEvent creation successful")
    
    # Test 8: JobProgressUpdatedEvent serialization
    print("\n8. Testing JobProgressUpdatedEvent serialization...")
    event_dict = progress_event.to_dict()
    assert event_dict["event_type"] == "JobProgressUpdatedEvent", "Event type should be correct"
    assert "progress" in event_dict, "Progress should be serialized"
    assert event_dict["progress"]["percentage"] == 50, "Progress percentage should be serialized"
    print("   ✓ JobProgressUpdatedEvent serialization successful")
    
    # Test 9: Event immutability
    print("\n9. Testing event immutability...")
    try:
        started_event.aggregate_id = "different-id"
        print("   ✗ Should not be able to modify frozen dataclass")
        return False
    except AttributeError:
        print("   ✓ Events are immutable (frozen dataclass)")
    
    # Test 10: occurred_at timestamp generation
    print("\n10. Testing occurred_at timestamp...")
    event_time = datetime.utcnow()
    test_event = JobStartedEvent(
        aggregate_id="job-456",
        occurred_at=event_time,
        url="https://youtube.com/watch?v=test2",
        format_id="140"
    )
    assert test_event.occurred_at == event_time, "Occurred at should be set correctly"
    assert isinstance(test_event.occurred_at, datetime), "Occurred at should be datetime"
    print("   ✓ occurred_at timestamp generation successful")
    
    print("\n=== Domain Events Tests Passed! ===")
    return True


# Test DownloadJob Entity
def test_download_job_creation():
    """Test DownloadJob entity creation and state transitions."""
    print("\n=== Testing DownloadJob Entity ===")
    
    # Test 1: Create job
    print("\n1. Testing job creation...")
    url = "https://youtube.com/watch?v=test"
    format_id = "137"
    job = DownloadJob.create(url, format_id)
    
    assert job.job_id is not None, "Job ID should be generated"
    assert job.url == url, "URL should match"
    assert str(job.format_id) == format_id, "Format ID should match"
    assert job.status == JobStatus.PENDING, "Initial status should be PENDING"
    assert job.progress.percentage == 0, "Initial progress should be 0"
    print("   ✓ Job creation successful")
    
    # Test 2: Start job and verify event
    print("\n2. Testing job start transition and event...")
    event = job.start()
    assert job.status == JobStatus.PROCESSING, "Status should be PROCESSING after start"
    assert job.progress.phase == "extracting metadata", "Phase should be metadata extraction"
    assert event is not None, "Start should return JobStartedEvent"
    assert isinstance(event, JobStartedEvent), "Event should be JobStartedEvent"
    assert event.aggregate_id == job.job_id, "Event aggregate_id should match job_id"
    assert event.url == url, "Event URL should match"
    assert event.format_id == format_id, "Event format_id should match"
    print("   ✓ Job start transition and event successful")
    
    # Test 3: Update progress
    print("\n3. Testing progress updates...")
    new_progress = JobProgress.downloading(50, speed="2 MB/s", eta=60)
    job.update_progress(new_progress)
    assert job.progress.percentage == 50, "Progress should be updated"
    assert job.progress.speed == "2 MB/s", "Speed should be updated"
    print("   ✓ Progress update successful")
    
    # Test 4: Complete job and verify event
    print("\n4. Testing job completion and event...")
    download_url = "http://example.com/download"
    expire_at = datetime.utcnow() + timedelta(minutes=10)
    event = job.complete(download_url, "token123", expire_at)
    assert job.status == JobStatus.COMPLETED, "Status should be COMPLETED"
    assert job.progress.percentage == 100, "Progress should be 100%"
    assert job.download_url == download_url, "Download URL should be set"
    assert isinstance(event, JobCompletedEvent), "Event should be JobCompletedEvent"
    assert event.aggregate_id == job.job_id, "Event aggregate_id should match job_id"
    assert event.download_url == download_url, "Event download_url should match"
    assert event.expire_at == expire_at, "Event expire_at should match"
    print("   ✓ Job completion and event successful")
    
    # Test 5: Invalid state transitions
    print("\n5. Testing invalid state transitions...")
    try:
        job.start()  # Can't start completed job
        print("   ✗ Should have raised ValueError")
        return False
    except ValueError:
        print("   ✓ Invalid transition correctly rejected")
    
    # Test 6: Fail job and verify event
    print("\n6. Testing job failure and event...")
    job2 = DownloadJob.create("https://youtube.com/watch?v=test2", "137")
    event = job2.fail("Test error", "TestError")
    assert job2.status == JobStatus.FAILED, "Status should be FAILED"
    assert job2.error_message == "Test error", "Error message should be set"
    assert isinstance(event, JobFailedEvent), "Event should be JobFailedEvent"
    assert event.aggregate_id == job2.job_id, "Event aggregate_id should match job_id"
    assert event.error_message == "Test error", "Event error_message should match"
    assert event.error_category == "TestError", "Event error_category should match"
    print("   ✓ Job failure and event successful")
    
    # Test 7: Cannot update progress on failed job
    print("\n7. Testing progress update on failed job...")
    try:
        job2.update_progress(JobProgress.downloading(50))
        print("   ✗ Should have raised ValueError")
        return False
    except ValueError:
        print("   ✓ Progress update correctly rejected on failed job")
    
    # Test 8: Terminal state checks
    print("\n8. Testing terminal state checks...")
    assert job.is_terminal() is True, "Completed job should be terminal"
    assert job2.is_terminal() is True, "Failed job should be terminal"
    job3 = DownloadJob.create("https://youtube.com/watch?v=test3", "137")
    assert job3.is_terminal() is False, "Pending job should not be terminal"
    print("   ✓ Terminal state checks successful")
    
    # Test 9: Idempotent start (no event when already processing)
    print("\n9. Testing idempotent start behavior...")
    job4 = DownloadJob.create("https://youtube.com/watch?v=test4", "137")
    first_event = job4.start()
    assert first_event is not None, "First start should return event"
    second_event = job4.start()
    assert second_event is None, "Second start should return None (idempotent)"
    assert job4.status == JobStatus.PROCESSING, "Status should still be PROCESSING"
    print("   ✓ Idempotent start behavior successful")
    
    print("\n=== DownloadJob Entity Tests Passed! ===")
    return True


def test_job_manager_service():
    """Test JobManager service logic."""
    print("\n=== Testing JobManager Service ===")
    
    repo = MockJobRepository()
    manager = JobManager(repo)
    
    # Test 1: Create job
    print("\n1. Testing job creation...")
    job = manager.create_job("https://youtube.com/watch?v=test", "137")
    assert job.job_id in repo.jobs, "Job should be saved in repository"
    print("   ✓ Job creation successful")
    
    # Test 2: Get job
    print("\n2. Testing job retrieval...")
    retrieved = manager.get_job(job.job_id)
    assert retrieved.job_id == job.job_id, "Retrieved job should match"
    print("   ✓ Job retrieval successful")
    
    # Test 3: Start job
    print("\n3. Testing job start...")
    started = manager.start_job(job.job_id)
    assert started.status == JobStatus.PROCESSING, "Job should be processing"
    print("   ✓ Job start successful")
    
    # Test 4: Update progress
    print("\n4. Testing progress updates...")
    for i in range(10, 101, 10):
        success = manager.update_job_progress(
            job.job_id,
            JobProgress.downloading(i, speed=f"{i/10} MB/s")
        )
        assert success is True, f"Progress update {i}% should succeed"
    print("   ✓ Progress updates successful")
    
    # Test 5: Complete job
    print("\n5. Testing job completion...")
    completed = manager.complete_job(
        job.job_id,
        download_url="http://example.com/download",
        download_token="token123",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    assert completed.status == JobStatus.COMPLETED, "Job should be completed"
    print("   ✓ Job completion successful")
    
    # Test 6: Get status info
    print("\n6. Testing status info retrieval...")
    info = manager.get_job_status_info(job.job_id)
    assert info["status"] == "completed", "Status should be completed"
    assert info["download_url"] is not None, "Download URL should be present"
    assert info["time_remaining"] is not None, "Time remaining should be calculated"
    print("   ✓ Status info retrieval successful")
    
    # Test 7: Fail job
    print("\n7. Testing job failure...")
    job2 = manager.create_job("https://youtube.com/watch?v=test2", "137")
    manager.start_job(job2.job_id)
    failed = manager.fail_job(job2.job_id, "Download error", "DownloadError")
    assert failed.status == JobStatus.FAILED, "Job should be failed"
    assert failed.error_category == "DownloadError", "Error category should be set"
    print("   ✓ Job failure successful")
    
    # Test 8: Delete job
    print("\n8. Testing job deletion...")
    deleted = manager.delete_job(job.job_id)
    assert deleted is True, "Job should be deleted"
    assert job.job_id not in repo.jobs, "Job should be removed from repository"
    print("   ✓ Job deletion successful")
    
    # Test 9: Job not found error
    print("\n9. Testing job not found error...")
    try:
        manager.get_job("nonexistent")
        print("   ✗ Should have raised JobNotFoundError")
        return False
    except JobNotFoundError:
        print("   ✓ JobNotFoundError raised correctly")
    
    # Test 10: Invalid state transition error
    print("\n10. Testing invalid state transition...")
    job3 = manager.create_job("https://youtube.com/watch?v=test3", "137")
    try:
        manager.complete_job(job3.job_id)  # Can't complete pending job
        print("   ✗ Should have raised JobStateError")
        return False
    except JobStateError:
        print("   ✓ JobStateError raised correctly")
    
    print("\n=== JobManager Service Tests Passed! ===")
    return True


def test_file_manager_service():
    """Test FileManager service logic."""
    print("\n=== Testing FileManager Service ===")
    
    repo = MockFileRepository()
    storage_repo = MockFileStorageRepository()
    manager = FileManager(repo, storage_repo)
    
    # Test 1: Register file
    print("\n1. Testing file registration...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test content")
        tmp_path = tmp.name
    
    try:
        file = manager.register_file(tmp_path, "job1", "test_video.mp4", ttl_minutes=10)
        assert file.token is not None, "Token should be generated"
        assert len(str(file.token)) > 0, "Token should not be empty"
        assert file.job_id == "job1", "Job ID should match"
        assert file.filename == "test_video.mp4", "Filename should match"
        assert str(file.token) in repo.files_by_token, "File should be saved in repository"
        print("   ✓ File registration successful")
        
        # Test 2: Get file by token
        print("\n2. Testing file retrieval by token...")
        retrieved = manager.get_file_by_token(str(file.token))
        assert str(retrieved.token) == str(file.token), "Retrieved file should match"
        assert retrieved.job_id == file.job_id, "Job ID should match"
        print("   ✓ File retrieval by token successful")
        
        # Test 3: Get file by job ID
        print("\n3. Testing file retrieval by job ID...")
        retrieved_by_job = manager.get_file_by_job_id("job1")
        assert retrieved_by_job is not None, "File should be found by job ID"
        assert str(retrieved_by_job.token) == str(file.token), "Token should match"
        print("   ✓ File retrieval by job ID successful")
        
        # Test 4: Validate token
        print("\n4. Testing token validation...")
        is_valid = manager.validate_token(str(file.token))
        assert is_valid is True, "Token should be valid"
        is_invalid = manager.validate_token("nonexistent")
        assert is_invalid is False, "Nonexistent token should be invalid"
        print("   ✓ Token validation successful")
        
        # Test 5: Get download URL
        print("\n5. Testing download URL generation...")
        url = manager.get_download_url(str(file.token), base_url="/api/v1/downloads")
        assert url == f"/api/v1/downloads/{str(file.token)}", "URL should be correct"
        print("   ✓ Download URL generation successful")
        
        # Test 6: Get file info
        print("\n6. Testing file info retrieval...")
        info = manager.get_file_info(str(file.token))
        assert info["token"] == str(file.token), "Token should match"
        assert info["filename"] == "test_video.mp4", "Filename should match"
        assert info["remaining_seconds"] > 0, "Remaining seconds should be positive"
        print("   ✓ File info retrieval successful")
        
        # Test 7: Delete file (verify storage repository is called)
        print("\n7. Testing file deletion...")
        deleted = manager.delete_file(str(file.token), delete_physical=True)
        assert deleted is True, "File should be deleted"
        assert str(file.token) not in repo.files_by_token, "File should be removed from repository"
        assert tmp_path in storage_repo.deleted_files, "Storage repository should be called to delete physical file"
        print("   ✓ File deletion successful")
        
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise e
    
    # Test 8: File not found error
    print("\n8. Testing file not found error...")
    try:
        manager.get_file_by_token("nonexistent")
        print("   ✗ Should have raised FileNotFoundError")
        return False
    except FileNotFoundError2:
        print("   ✓ FileNotFoundError raised correctly")
    
    # Test 9: Expired file handling
    print("\n9. Testing expired file handling...")
    expired = DownloadedFile(
        file_path="/tmp/expired.mp4",
        token="expired-token",
        job_id="job2",
        filename="expired.mp4",
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        created_at=datetime.utcnow() - timedelta(minutes=11)
    )
    repo.save(expired)
    
    try:
        manager.get_file_by_token("expired-token")
        print("   ✗ Should have raised FileExpiredError")
        return False
    except FileExpiredError:
        print("   ✓ FileExpiredError raised correctly")
        assert "expired-token" not in repo.files_by_token, "Expired file should be deleted"
    
    # Test 10: Cleanup expired files (verify storage repository is called)
    print("\n10. Testing cleanup of expired files...")
    expired1 = DownloadedFile(
        file_path="/tmp/expired1.mp4",
        token="token1",
        job_id="job3",
        filename="expired1.mp4",
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        created_at=datetime.utcnow() - timedelta(minutes=11)
    )
    expired2 = DownloadedFile(
        file_path="/tmp/expired2.mp4",
        token="token2",
        job_id="job4",
        filename="expired2.mp4",
        expires_at=datetime.utcnow() - timedelta(minutes=2),
        created_at=datetime.utcnow() - timedelta(minutes=12)
    )
    repo.save(expired1)
    repo.save(expired2)
    
    # Clear previous deleted files
    storage_repo.deleted_files.clear()
    
    count = manager.cleanup_expired_files()
    assert count == 2, "Should cleanup 2 expired files"
    assert "token1" not in repo.files_by_token, "Expired file 1 should be removed"
    assert "token2" not in repo.files_by_token, "Expired file 2 should be removed"
    assert "/tmp/expired1.mp4" in storage_repo.deleted_files, "Storage repository should delete expired file 1"
    assert "/tmp/expired2.mp4" in storage_repo.deleted_files, "Storage repository should delete expired file 2"
    print("   ✓ Cleanup of expired files successful")
    
    # Test 11: Unique token generation
    print("\n11. Testing unique token generation...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp1:
        tmp1.write(b"content1")
        tmp1_path = tmp1.name
    with tempfile.NamedTemporaryFile(delete=False) as tmp2:
        tmp2.write(b"content2")
        tmp2_path = tmp2.name
    
    try:
        file1 = manager.register_file(tmp1_path, "job5", "file1.mp4")
        file2 = manager.register_file(tmp2_path, "job6", "file2.mp4")
        assert file1.token != file2.token, "Tokens should be unique"
        print("   ✓ Unique token generation successful")
    finally:
        if os.path.exists(tmp1_path):
            os.unlink(tmp1_path)
        if os.path.exists(tmp2_path):
            os.unlink(tmp2_path)
    
    # Test 12: Verify no direct filesystem operations in FileManager
    print("\n12. Testing that FileManager delegates to storage repository...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp3:
        tmp3.write(b"test content")
        tmp3_path = tmp3.name
    
    try:
        # Register a file
        file3 = manager.register_file(tmp3_path, "job7", "test3.mp4")
        
        # Clear the deleted files list
        storage_repo.deleted_files.clear()
        
        # Delete the file
        manager.delete_file(str(file3.token), delete_physical=True)
        
        # Verify storage repository was called
        assert len(storage_repo.deleted_files) == 1, "Storage repository should be called once"
        assert tmp3_path in storage_repo.deleted_files, "Correct file path should be passed to storage repository"
        print("   ✓ FileManager correctly delegates to storage repository")
        
    finally:
        if os.path.exists(tmp3_path):
            os.unlink(tmp3_path)
    
    # Test 13: Test delete_file with delete_physical=False
    print("\n13. Testing delete_file with delete_physical=False...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp4:
        tmp4.write(b"test content")
        tmp4_path = tmp4.name
    
    try:
        file4 = manager.register_file(tmp4_path, "job8", "test4.mp4")
        storage_repo.deleted_files.clear()
        
        # Delete metadata only
        manager.delete_file(str(file4.token), delete_physical=False)
        
        # Verify storage repository was NOT called
        assert len(storage_repo.deleted_files) == 0, "Storage repository should not be called when delete_physical=False"
        assert str(file4.token) not in repo.files_by_token, "Metadata should still be deleted"
        print("   ✓ delete_physical=False works correctly")
        
    finally:
        if os.path.exists(tmp4_path):
            os.unlink(tmp4_path)
    
    print("\n=== FileManager Service Tests Passed! ===")
    return True


def main():
    """Run all domain unit tests."""
    print("=" * 60)
    print("Domain Unit Tests")
    print("=" * 60)
    
    tests = [
        ("Domain Events", test_domain_events),
        ("DownloadJob Entity", test_download_job_creation),
        ("JobManager Service", test_job_manager_service),
        ("FileManager Service", test_file_manager_service),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 60}")
            print(f"Running: {test_name}")
            print('=' * 60)
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return all(result for _, result in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
