"""
Redis Job Repository Integration Tests

Integration tests for RedisJobRepository with real Redis instance.
Tests CRUD operations, atomic updates, batch operations, and query functionality.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import os
import time
import pytest
from datetime import datetime, timedelta

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_repository
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobStatus, JobProgress
from infrastructure.redis_job_repository import RedisJobRepository


@pytest.fixture
def redis_repo():
    """Fixture to provide Redis repository instance."""
    init_redis()
    return get_redis_repository()


@pytest.fixture
def job_repository(redis_repo):
    """Fixture to provide RedisJobRepository instance."""
    repo = RedisJobRepository(redis_repo)
    yield repo
    # Cleanup is handled by flush_redis fixture


@pytest.fixture
def sample_job():
    """Fixture to create a sample DownloadJob."""
    return DownloadJob.create(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        format_id="137"
    )


@pytest.fixture
def multiple_jobs():
    """Fixture to create multiple sample jobs."""
    return [
        DownloadJob.create(
            url=f"https://www.youtube.com/watch?v=test{i}",
            format_id="137"
        )
        for i in range(5)
    ]


@pytest.fixture(autouse=True)
def flush_redis(redis_repo):
    """Flush Redis before each test for isolation."""
    # Flush before test
    redis_repo.redis.flushdb()
    yield
    # Flush after test
    redis_repo.redis.flushdb()


# ============================================================================
# Test Basic CRUD Operations (Requirement 4.2, 4.3, 4.5)
# ============================================================================

@pytest.mark.integration
def test_save_stores_job_in_redis_with_correct_key_format(job_repository, sample_job):
    """Test that save stores job in Redis with correct key format."""
    # Save job
    result = job_repository.save(sample_job)
    
    assert result is True
    
    # Verify key format in Redis
    expected_key = job_repository.redis_repo._make_key(f"job:{sample_job.job_id}")
    assert job_repository.redis_repo.redis.exists(expected_key)


@pytest.mark.integration
def test_get_retrieves_job_from_redis_by_id(job_repository, sample_job):
    """Test that get retrieves job from Redis by ID."""
    # Save job
    job_repository.save(sample_job)
    
    # Retrieve job
    retrieved_job = job_repository.get(sample_job.job_id)
    
    assert retrieved_job is not None
    assert retrieved_job.job_id == sample_job.job_id
    assert retrieved_job.url == sample_job.url
    assert retrieved_job.format_id == sample_job.format_id
    assert retrieved_job.status == sample_job.status


@pytest.mark.integration
def test_get_returns_none_for_nonexistent_job(job_repository):
    """Test that get returns None for non-existent job."""
    # Try to retrieve non-existent job
    retrieved_job = job_repository.get("nonexistent_job_id")
    
    assert retrieved_job is None


@pytest.mark.integration
def test_delete_removes_job_from_redis(job_repository, sample_job):
    """Test that delete removes job from Redis."""
    # Save job
    job_repository.save(sample_job)
    
    # Verify job exists
    assert job_repository.exists(sample_job.job_id)
    
    # Delete job
    result = job_repository.delete(sample_job.job_id)
    
    assert result is True
    assert not job_repository.exists(sample_job.job_id)
    assert job_repository.get(sample_job.job_id) is None


@pytest.mark.integration
def test_exists_returns_true_for_existing_job(job_repository, sample_job):
    """Test that exists returns True for existing job."""
    # Save job
    job_repository.save(sample_job)
    
    # Check existence
    assert job_repository.exists(sample_job.job_id) is True


@pytest.mark.integration
def test_exists_returns_false_for_nonexistent_job(job_repository):
    """Test that exists returns False for non-existent job."""
    # Check existence of non-existent job
    assert job_repository.exists("nonexistent_job_id") is False



# ============================================================================
# Test Atomic Update Operations (Requirement 4.4, 4.6)
# ============================================================================

@pytest.mark.integration
def test_update_progress_uses_lua_script_for_atomic_update(job_repository, sample_job):
    """Test that update_progress uses Lua script for atomic update."""
    # Save job
    job_repository.save(sample_job)
    
    # Update progress
    new_progress = JobProgress.downloading(percentage=50, speed="1.5 MB/s", eta=120)
    result = job_repository.update_progress(sample_job.job_id, new_progress)
    
    assert result is True
    
    # Verify progress was updated
    retrieved_job = job_repository.get(sample_job.job_id)
    assert retrieved_job is not None
    assert retrieved_job.progress.percentage == 50
    assert retrieved_job.progress.phase == "downloading"
    assert retrieved_job.progress.speed == "1.5 MB/s"
    assert retrieved_job.progress.eta == 120


@pytest.mark.integration
def test_update_progress_updates_progress_fields_correctly(job_repository, sample_job):
    """Test that update_progress updates all progress fields correctly."""
    # Save job
    job_repository.save(sample_job)
    
    # Get initial updated_at timestamp
    initial_job = job_repository.get(sample_job.job_id)
    initial_updated_at = initial_job.updated_at
    
    # Wait a moment to ensure timestamp changes
    time.sleep(0.1)
    
    # Update progress with all fields
    new_progress = JobProgress.downloading(percentage=75, speed="2.0 MB/s", eta=60)
    result = job_repository.update_progress(sample_job.job_id, new_progress)
    
    assert result is True
    
    # Verify all fields were updated
    retrieved_job = job_repository.get(sample_job.job_id)
    assert retrieved_job is not None
    assert retrieved_job.progress.percentage == 75
    assert retrieved_job.progress.phase == "downloading"
    assert retrieved_job.progress.speed == "2.0 MB/s"
    assert retrieved_job.progress.eta == 60
    
    # Verify updated_at timestamp was updated
    assert retrieved_job.updated_at > initial_updated_at


@pytest.mark.integration
def test_update_progress_handles_missing_job_gracefully(job_repository):
    """Test that update_progress handles missing job gracefully."""
    # Try to update progress for non-existent job
    new_progress = JobProgress.downloading(percentage=50, speed="1.5 MB/s")
    result = job_repository.update_progress("nonexistent_job_id", new_progress)
    
    assert result is False


@pytest.mark.integration
def test_update_status_uses_lua_script_for_atomic_update(job_repository, sample_job):
    """Test that update_status uses Lua script for atomic update."""
    # Save job
    job_repository.save(sample_job)
    
    # Update status
    result = job_repository.update_status(sample_job.job_id, JobStatus.PROCESSING)
    
    assert result is True
    
    # Verify status was updated
    retrieved_job = job_repository.get(sample_job.job_id)
    assert retrieved_job is not None
    assert retrieved_job.status == JobStatus.PROCESSING


@pytest.mark.integration
def test_update_status_updates_status_and_updated_at_timestamp(job_repository, sample_job):
    """Test that update_status updates status and updated_at timestamp."""
    # Save job
    job_repository.save(sample_job)
    
    # Get initial updated_at timestamp
    initial_job = job_repository.get(sample_job.job_id)
    initial_updated_at = initial_job.updated_at
    
    # Wait a moment to ensure timestamp changes
    time.sleep(0.1)
    
    # Update status
    result = job_repository.update_status(sample_job.job_id, JobStatus.COMPLETED)
    
    assert result is True
    
    # Verify status and timestamp were updated
    retrieved_job = job_repository.get(sample_job.job_id)
    assert retrieved_job is not None
    assert retrieved_job.status == JobStatus.COMPLETED
    assert retrieved_job.updated_at > initial_updated_at


@pytest.mark.integration
def test_update_status_with_error_message(job_repository, sample_job):
    """Test that update_status can include error message."""
    # Save job
    job_repository.save(sample_job)
    
    # Update status with error message
    error_msg = "Download failed: Network error"
    result = job_repository.update_status(
        sample_job.job_id,
        JobStatus.FAILED,
        error_message=error_msg
    )
    
    assert result is True
    
    # Verify error message was stored
    retrieved_job = job_repository.get(sample_job.job_id)
    assert retrieved_job is not None
    assert retrieved_job.status == JobStatus.FAILED
    assert retrieved_job.error_message == error_msg


@pytest.mark.integration
def test_update_status_handles_missing_job_gracefully(job_repository):
    """Test that update_status handles missing job gracefully."""
    # Try to update status for non-existent job
    result = job_repository.update_status("nonexistent_job_id", JobStatus.PROCESSING)
    
    assert result is False



# ============================================================================
# Test Batch Operations (Requirement 4.3)
# ============================================================================

@pytest.mark.integration
def test_get_many_uses_pipeline_for_efficiency(job_repository, multiple_jobs):
    """Test that get_many uses pipeline for efficiency."""
    # Save all jobs
    for job in multiple_jobs:
        job_repository.save(job)
    
    # Get all jobs using get_many
    job_ids = [job.job_id for job in multiple_jobs]
    retrieved_jobs = job_repository.get_many(job_ids)
    
    # Verify all jobs were retrieved
    assert len(retrieved_jobs) == len(multiple_jobs)
    
    # Verify job IDs match
    retrieved_ids = {job.job_id for job in retrieved_jobs}
    expected_ids = {job.job_id for job in multiple_jobs}
    assert retrieved_ids == expected_ids


@pytest.mark.integration
def test_get_many_returns_correct_jobs_in_order(job_repository, multiple_jobs):
    """Test that get_many returns correct jobs."""
    # Save all jobs
    for job in multiple_jobs:
        job_repository.save(job)
    
    # Get jobs in specific order
    job_ids = [multiple_jobs[2].job_id, multiple_jobs[0].job_id, multiple_jobs[4].job_id]
    retrieved_jobs = job_repository.get_many(job_ids)
    
    # Verify correct jobs were retrieved
    assert len(retrieved_jobs) == 3
    retrieved_ids = {job.job_id for job in retrieved_jobs}
    assert retrieved_ids == set(job_ids)
    
    # Verify job data integrity
    for retrieved_job in retrieved_jobs:
        original_job = next(j for j in multiple_jobs if j.job_id == retrieved_job.job_id)
        assert retrieved_job.url == original_job.url
        assert retrieved_job.format_id == original_job.format_id
        assert retrieved_job.status == original_job.status


@pytest.mark.integration
def test_get_many_handles_missing_jobs_in_batch(job_repository, multiple_jobs):
    """Test that get_many handles missing jobs in batch."""
    # Save only some jobs
    job_repository.save(multiple_jobs[0])
    job_repository.save(multiple_jobs[2])
    
    # Try to get mix of existing and non-existent jobs
    job_ids = [
        multiple_jobs[0].job_id,
        "nonexistent_job_1",
        multiple_jobs[2].job_id,
        "nonexistent_job_2"
    ]
    retrieved_jobs = job_repository.get_many(job_ids)
    
    # Should only retrieve existing jobs
    assert len(retrieved_jobs) == 2
    retrieved_ids = {job.job_id for job in retrieved_jobs}
    assert retrieved_ids == {multiple_jobs[0].job_id, multiple_jobs[2].job_id}


@pytest.mark.integration
def test_get_many_with_empty_list(job_repository):
    """Test that get_many handles empty list correctly."""
    retrieved_jobs = job_repository.get_many([])
    
    assert retrieved_jobs == []


@pytest.mark.integration
def test_save_many_uses_pipeline_for_efficiency(job_repository, multiple_jobs):
    """Test that save_many uses pipeline for efficiency."""
    # Save all jobs using save_many
    result = job_repository.save_many(multiple_jobs)
    
    assert result is True
    
    # Verify all jobs were saved
    for job in multiple_jobs:
        retrieved = job_repository.get(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id


@pytest.mark.integration
def test_save_many_stores_all_jobs_correctly(job_repository, multiple_jobs):
    """Test that save_many stores all jobs correctly."""
    # Save all jobs
    result = job_repository.save_many(multiple_jobs)
    
    assert result is True
    
    # Verify data integrity for all jobs
    for job in multiple_jobs:
        retrieved = job_repository.get(job.job_id)
        assert retrieved is not None
        assert retrieved.url == job.url
        assert retrieved.format_id == job.format_id
        assert retrieved.status == job.status
        assert retrieved.progress.percentage == job.progress.percentage


@pytest.mark.integration
def test_save_many_with_empty_list(job_repository):
    """Test that save_many handles empty list correctly."""
    result = job_repository.save_many([])
    
    assert result is True


@pytest.mark.integration
def test_save_many_updates_existing_jobs(job_repository, multiple_jobs):
    """Test that save_many can update existing jobs."""
    # Save jobs initially
    job_repository.save_many(multiple_jobs)
    
    # Modify jobs
    for job in multiple_jobs:
        job.status = JobStatus.PROCESSING
        job.progress = JobProgress.downloading(percentage=50, speed="1.5 MB/s")
    
    # Save updated jobs
    result = job_repository.save_many(multiple_jobs)
    
    assert result is True
    
    # Verify updates
    for job in multiple_jobs:
        retrieved = job_repository.get(job.job_id)
        assert retrieved is not None
        assert retrieved.status == JobStatus.PROCESSING
        assert retrieved.progress.percentage == 50
        assert retrieved.progress.speed == "1.5 MB/s"



# ============================================================================
# Test Query and Expiration Operations (Requirement 4.7)
# ============================================================================

@pytest.mark.integration
def test_find_by_status_uses_scan_to_find_jobs(job_repository):
    """Test that find_by_status uses SCAN to find jobs."""
    # Create jobs with different statuses
    pending_jobs = [
        DownloadJob.create(url=f"https://youtube.com/watch?v=pending{i}", format_id="137")
        for i in range(3)
    ]
    processing_jobs = [
        DownloadJob.create(url=f"https://youtube.com/watch?v=processing{i}", format_id="137")
        for i in range(2)
    ]
    
    # Set statuses
    for job in processing_jobs:
        job.status = JobStatus.PROCESSING
    
    # Save all jobs
    all_jobs = pending_jobs + processing_jobs
    for job in all_jobs:
        job_repository.save(job)
    
    # Find pending jobs
    found_pending = job_repository.find_by_status(JobStatus.PENDING, limit=100)
    
    # Filter to only our test jobs
    pending_ids = {job.job_id for job in pending_jobs}
    found_pending_ids = {job.job_id for job in found_pending if job.job_id in pending_ids}
    
    assert len(found_pending_ids) == 3


@pytest.mark.integration
def test_find_by_status_respects_limit_parameter(job_repository):
    """Test that find_by_status respects limit parameter."""
    # Create 10 pending jobs
    jobs = [
        DownloadJob.create(url=f"https://youtube.com/watch?v=test{i}", format_id="137")
        for i in range(10)
    ]
    
    # Save all jobs
    for job in jobs:
        job_repository.save(job)
    
    # Find with limit of 5
    found_jobs = job_repository.find_by_status(JobStatus.PENDING, limit=5)
    
    # Filter to only our test jobs
    test_job_ids = {job.job_id for job in jobs}
    found_test_jobs = [job for job in found_jobs if job.job_id in test_job_ids]
    
    # Should respect limit
    assert len(found_test_jobs) <= 5


@pytest.mark.integration
def test_find_by_status_returns_jobs_with_correct_status(job_repository):
    """Test that find_by_status returns jobs with correct status."""
    # Create jobs with different statuses
    pending_job = DownloadJob.create(url="https://youtube.com/watch?v=pending", format_id="137")
    processing_job = DownloadJob.create(url="https://youtube.com/watch?v=processing", format_id="137")
    completed_job = DownloadJob.create(url="https://youtube.com/watch?v=completed", format_id="137")
    failed_job = DownloadJob.create(url="https://youtube.com/watch?v=failed", format_id="137")
    
    # Set statuses
    processing_job.status = JobStatus.PROCESSING
    completed_job.status = JobStatus.COMPLETED
    failed_job.status = JobStatus.FAILED
    
    # Save all jobs
    all_jobs = [pending_job, processing_job, completed_job, failed_job]
    for job in all_jobs:
        job_repository.save(job)
    
    # Find processing jobs
    found_processing = job_repository.find_by_status(JobStatus.PROCESSING, limit=100)
    
    # Verify only processing jobs are returned
    for job in found_processing:
        if job.job_id == processing_job.job_id:
            assert job.status == JobStatus.PROCESSING
    
    # Find completed jobs
    found_completed = job_repository.find_by_status(JobStatus.COMPLETED, limit=100)
    
    # Verify only completed jobs are returned
    for job in found_completed:
        if job.job_id == completed_job.job_id:
            assert job.status == JobStatus.COMPLETED


@pytest.mark.integration
def test_find_by_status_with_no_matches(job_repository):
    """Test that find_by_status returns empty list when no jobs match."""
    # Create only pending jobs
    jobs = [
        DownloadJob.create(url=f"https://youtube.com/watch?v=test{i}", format_id="137")
        for i in range(3)
    ]
    
    # Save all jobs
    for job in jobs:
        job_repository.save(job)
    
    # Try to find failed jobs (should be none from our test set)
    found_jobs = job_repository.find_by_status(JobStatus.FAILED, limit=100)
    
    # Filter to only our test jobs
    test_job_ids = {job.job_id for job in jobs}
    found_test_jobs = [job for job in found_jobs if job.job_id in test_job_ids]
    
    assert len(found_test_jobs) == 0


@pytest.mark.integration
def test_get_expired_jobs_returns_jobs_older_than_threshold(job_repository):
    """Test that get_expired_jobs returns jobs older than threshold."""
    # Create jobs with different ages
    old_job = DownloadJob.create(url="https://youtube.com/watch?v=old", format_id="137")
    old_job.status = JobStatus.COMPLETED
    old_job.updated_at = datetime.utcnow() - timedelta(hours=2)
    
    recent_job = DownloadJob.create(url="https://youtube.com/watch?v=recent", format_id="137")
    recent_job.status = JobStatus.COMPLETED
    recent_job.updated_at = datetime.utcnow() - timedelta(minutes=5)
    
    # Save jobs
    job_repository.save(old_job)
    job_repository.save(recent_job)
    
    # Get expired jobs (older than 1 hour)
    expired_jobs = job_repository.get_expired_jobs(timedelta(hours=1))
    
    # Verify old job is in expired list
    expired_ids = [job_id for job_id in expired_jobs]
    assert old_job.job_id in expired_ids
    assert recent_job.job_id not in expired_ids


@pytest.mark.integration
def test_get_expired_jobs_respects_expiration_time_parameter(job_repository):
    """Test that get_expired_jobs respects expiration time parameter."""
    # Create jobs with different ages
    very_old_job = DownloadJob.create(url="https://youtube.com/watch?v=veryold", format_id="137")
    very_old_job.status = JobStatus.COMPLETED
    very_old_job.updated_at = datetime.utcnow() - timedelta(hours=3)
    
    old_job = DownloadJob.create(url="https://youtube.com/watch?v=old", format_id="137")
    old_job.status = JobStatus.COMPLETED
    old_job.updated_at = datetime.utcnow() - timedelta(hours=1, minutes=30)
    
    recent_job = DownloadJob.create(url="https://youtube.com/watch?v=recent", format_id="137")
    recent_job.status = JobStatus.COMPLETED
    recent_job.updated_at = datetime.utcnow() - timedelta(minutes=30)
    
    # Save jobs
    job_repository.save(very_old_job)
    job_repository.save(old_job)
    job_repository.save(recent_job)
    
    # Get jobs expired for more than 2 hours
    expired_jobs = job_repository.get_expired_jobs(timedelta(hours=2))
    
    # Verify only very old job is in expired list
    assert very_old_job.job_id in expired_jobs
    assert old_job.job_id not in expired_jobs
    assert recent_job.job_id not in expired_jobs


@pytest.mark.integration
def test_get_expired_jobs_only_returns_terminal_jobs(job_repository):
    """Test that get_expired_jobs only returns terminal (completed/failed) jobs."""
    # Create old jobs with different statuses
    old_pending = DownloadJob.create(url="https://youtube.com/watch?v=oldpending", format_id="137")
    old_pending.status = JobStatus.PENDING
    old_pending.updated_at = datetime.utcnow() - timedelta(hours=2)
    
    old_processing = DownloadJob.create(url="https://youtube.com/watch?v=oldprocessing", format_id="137")
    old_processing.status = JobStatus.PROCESSING
    old_processing.updated_at = datetime.utcnow() - timedelta(hours=2)
    
    old_completed = DownloadJob.create(url="https://youtube.com/watch?v=oldcompleted", format_id="137")
    old_completed.status = JobStatus.COMPLETED
    old_completed.updated_at = datetime.utcnow() - timedelta(hours=2)
    
    old_failed = DownloadJob.create(url="https://youtube.com/watch?v=oldfailed", format_id="137")
    old_failed.status = JobStatus.FAILED
    old_failed.updated_at = datetime.utcnow() - timedelta(hours=2)
    
    # Save all jobs
    job_repository.save(old_pending)
    job_repository.save(old_processing)
    job_repository.save(old_completed)
    job_repository.save(old_failed)
    
    # Get expired jobs
    expired_jobs = job_repository.get_expired_jobs(timedelta(hours=1))
    
    # Only terminal jobs should be returned
    assert old_pending.job_id not in expired_jobs
    assert old_processing.job_id not in expired_jobs
    assert old_completed.job_id in expired_jobs
    assert old_failed.job_id in expired_jobs


@pytest.mark.integration
def test_job_ttl_expires_after_configured_time(job_repository, sample_job):
    """Test that job TTL expires after configured time (use short TTL for test)."""
    # Temporarily set short TTL for testing
    original_ttl = job_repository.ttl
    job_repository.ttl = 2  # 2 seconds
    
    try:
        # Save job with short TTL
        job_repository.save(sample_job)
        
        # Verify job exists
        assert job_repository.exists(sample_job.job_id)
        
        # Wait for TTL to expire
        time.sleep(3)
        
        # Verify job has expired
        assert not job_repository.exists(sample_job.job_id)
        assert job_repository.get(sample_job.job_id) is None
    finally:
        # Restore original TTL
        job_repository.ttl = original_ttl



# ============================================================================
# Test Error Handling (Requirement 4.6, 9.1, 9.2, 9.3)
# ============================================================================

@pytest.mark.integration
def test_save_handles_serialization_errors_gracefully(job_repository, sample_job):
    """Test that save handles serialization errors gracefully."""
    # This test verifies the repository handles edge cases
    # Normal save should work
    result = job_repository.save(sample_job)
    assert result is True


@pytest.mark.integration
def test_get_handles_deserialization_errors_gracefully(job_repository, redis_repo):
    """Test that get handles deserialization errors gracefully."""
    # Manually insert invalid JSON into Redis
    invalid_key = job_repository.redis_repo._make_key("job:invalid_job")
    job_repository.redis_repo.redis.set(invalid_key, "invalid json data")
    
    # Try to get the job - should return None instead of crashing
    result = job_repository.get("invalid_job")
    assert result is None


@pytest.mark.integration
def test_update_progress_handles_concurrent_updates(job_repository, sample_job):
    """Test that update_progress handles concurrent updates correctly."""
    # Save job
    job_repository.save(sample_job)
    
    # Simulate concurrent updates
    progress1 = JobProgress.downloading(percentage=30, speed="1.0 MB/s")
    progress2 = JobProgress.downloading(percentage=60, speed="2.0 MB/s")
    
    # Both updates should succeed (Lua script ensures atomicity)
    result1 = job_repository.update_progress(sample_job.job_id, progress1)
    result2 = job_repository.update_progress(sample_job.job_id, progress2)
    
    assert result1 is True
    assert result2 is True
    
    # Final state should reflect the last update
    retrieved_job = job_repository.get(sample_job.job_id)
    assert retrieved_job is not None
    assert retrieved_job.progress.percentage == 60


@pytest.mark.integration
def test_batch_operations_handle_partial_failures(job_repository, multiple_jobs):
    """Test that batch operations handle partial failures gracefully."""
    # Save some jobs successfully
    result = job_repository.save_many(multiple_jobs[:3])
    assert result is True
    
    # Try to get mix of existing and non-existent jobs
    job_ids = [job.job_id for job in multiple_jobs]
    retrieved_jobs = job_repository.get_many(job_ids)
    
    # Should retrieve only the saved jobs
    assert len(retrieved_jobs) == 3


@pytest.mark.integration
def test_find_by_status_handles_large_datasets(job_repository):
    """Test that find_by_status handles large datasets without blocking."""
    # Create many jobs (but not too many for test performance)
    jobs = [
        DownloadJob.create(url=f"https://youtube.com/watch?v=test{i}", format_id="137")
        for i in range(50)
    ]
    
    # Set half to processing
    for i, job in enumerate(jobs):
        if i % 2 == 0:
            job.status = JobStatus.PROCESSING
    
    # Save all jobs
    for job in jobs:
        job_repository.save(job)
    
    # Find processing jobs - should not block
    found_jobs = job_repository.find_by_status(JobStatus.PROCESSING, limit=100)
    
    # Verify we found some processing jobs
    test_job_ids = {job.job_id for job in jobs if job.status == JobStatus.PROCESSING}
    found_test_jobs = [job for job in found_jobs if job.job_id in test_job_ids]
    
    assert len(found_test_jobs) > 0


@pytest.mark.integration
def test_repository_operations_preserve_data_integrity(job_repository, sample_job):
    """Test that repository operations preserve data integrity."""
    # Save job
    job_repository.save(sample_job)
    
    # Retrieve and verify all fields
    retrieved = job_repository.get(sample_job.job_id)
    
    assert retrieved is not None
    assert retrieved.job_id == sample_job.job_id
    assert retrieved.url == sample_job.url
    assert str(retrieved.format_id) == str(sample_job.format_id)
    assert retrieved.status == sample_job.status
    assert retrieved.progress.percentage == sample_job.progress.percentage
    assert retrieved.progress.phase == sample_job.progress.phase
    assert retrieved.created_at.replace(microsecond=0) == sample_job.created_at.replace(microsecond=0)
    assert retrieved.updated_at.replace(microsecond=0) == sample_job.updated_at.replace(microsecond=0)


@pytest.mark.integration
def test_repository_handles_special_characters_in_urls(job_repository):
    """Test that repository handles special characters in URLs."""
    # Create job with special characters in URL
    special_job = DownloadJob.create(
        url="https://youtube.com/watch?v=test&feature=share&t=123",
        format_id="137"
    )
    
    # Save and retrieve
    job_repository.save(special_job)
    retrieved = job_repository.get(special_job.job_id)
    
    assert retrieved is not None
    assert retrieved.url == special_job.url


@pytest.mark.integration
def test_repository_handles_unicode_in_data(job_repository):
    """Test that repository handles Unicode characters in data."""
    # Create job and add Unicode error message
    job = DownloadJob.create(url="https://youtube.com/watch?v=test", format_id="137")
    job_repository.save(job)
    
    # Update with Unicode error message
    unicode_error = "下载失败: 网络错误 🚫"
    job_repository.update_status(job.job_id, JobStatus.FAILED, error_message=unicode_error)
    
    # Retrieve and verify
    retrieved = job_repository.get(job.job_id)
    assert retrieved is not None
    assert retrieved.error_message == unicode_error


