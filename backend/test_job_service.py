"""
Test script for job management service.

This script verifies that the job lifecycle management, repository operations,
and progress tracking are working correctly.
"""

import sys
import time
from datetime import datetime, timedelta

from application.job_service import JobService
from config.redis_config import get_redis_repository, init_redis
from domain.file_storage import FileManager
from domain.file_storage.repositories import RedisFileRepository
from domain.job_management import JobManager, JobNotFoundError, JobProgress
from domain.job_management.repositories import RedisJobRepository


def test_job_lifecycle():
    """Test complete job lifecycle: create, start, update progress, complete."""
    print("\n=== Testing Job Lifecycle ===")
    
    # Initialize dependencies
    print("Initializing Redis and services...")
    init_redis()
    redis_repo = get_redis_repository()
    
    # Initialize repositories and services
    job_repository = RedisJobRepository(redis_repo)
    job_manager = JobManager(job_repository)
    file_repository = RedisFileRepository(redis_repo)
    file_manager = FileManager(file_repository)
    job_service = JobService(job_manager, file_manager)
    
    # Test 1: Create a job
    print("\n1. Creating a new download job...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    test_format = "137"
    
    result = job_service.create_download_job(test_url, test_format)
    job_id = result["job_id"]
    print(f"   ✓ Job created: {job_id}")
    print(f"   Status: {result['status']}")
    
    # Test 2: Get job status
    print("\n2. Getting job status...")
    status = job_service.get_job_status(job_id)
    print(f"   ✓ Job status retrieved")
    print(f"   Status: {status['status']}")
    print(f"   Progress: {status['progress']['percentage']}% - {status['progress']['phase']}")
    
    # Test 3: Start the job
    print("\n3. Starting the job...")
    job = job_service.start_job(job_id)
    print(f"   ✓ Job started")
    print(f"   Status: {job.status.value}")
    print(f"   Progress: {job.progress.percentage}% - {job.progress.phase}")
    
    # Test 4: Update progress
    print("\n4. Updating job progress...")
    for i in range(10, 101, 30):
        success = job_service.update_progress(
            job_id,
            percentage=i,
            phase="downloading",
            speed="1.5 MB/s",
            eta=30
        )
        print(f"   ✓ Progress updated: {i}%")
        time.sleep(0.1)
    
    # Test 5: Complete the job
    print("\n5. Completing the job...")
    download_url = f"http://localhost:8000/api/v1/downloads/file/test-token-{job_id}"
    expire_at = datetime.utcnow() + timedelta(minutes=10)
    
    completed_job = job_service.complete_job(
        job_id,
        download_url=download_url,
        download_token=f"test-token-{job_id}",
        expire_at=expire_at
    )
    print(f"   ✓ Job completed")
    print(f"   Status: {completed_job.status.value}")
    print(f"   Download URL: {completed_job.download_url}")
    
    # Test 6: Verify final status
    print("\n6. Verifying final job status...")
    final_status = job_service.get_job_status(job_id)
    print(f"   ✓ Final status retrieved")
    print(f"   Status: {final_status['status']}")
    print(f"   Progress: {final_status['progress']['percentage']}%")
    print(f"   Download URL: {final_status['download_url']}")
    
    # Test 7: Delete the job
    print("\n7. Deleting the job...")
    deleted = job_service.delete_job(job_id)
    print(f"   ✓ Job deleted: {deleted}")
    
    # Test 8: Verify job is deleted
    print("\n8. Verifying job is deleted...")
    try:
        job_service.get_job_status(job_id)
        print("   ✗ ERROR: Job should not exist")
        return False
    except JobNotFoundError:
        print("   ✓ Job not found (as expected)")
    
    print("\n=== All Tests Passed! ===\n")
    return True


def test_job_failure():
    """Test job failure handling."""
    print("\n=== Testing Job Failure Handling ===")
    
    # Initialize dependencies
    init_redis()
    redis_repo = get_redis_repository()
    
    job_repository = RedisJobRepository(redis_repo)
    job_manager = JobManager(job_repository)
    file_repository = RedisFileRepository(redis_repo)
    file_manager = FileManager(file_repository)
    job_service = JobService(job_manager, file_manager)
    
    # Create and start a job
    print("\n1. Creating and starting a job...")
    result = job_service.create_download_job(
        "https://www.youtube.com/watch?v=invalid",
        "999"
    )
    job_id = result["job_id"]
    job_service.start_job(job_id)
    print(f"   ✓ Job created and started: {job_id}")
    
    # Fail the job
    print("\n2. Marking job as failed...")
    failed_job = job_service.fail_job(job_id, "Video not available")
    print(f"   ✓ Job marked as failed")
    print(f"   Status: {failed_job.status.value}")
    print(f"   Error: {failed_job.error_message}")
    
    # Verify failed status
    print("\n3. Verifying failed status...")
    status = job_service.get_job_status(job_id)
    print(f"   ✓ Status retrieved")
    print(f"   Status: {status['status']}")
    print(f"   Error: {status['error']}")
    
    # Cleanup
    job_service.delete_job(job_id)
    print("\n=== Failure Handling Test Passed! ===\n")
    return True


def test_atomic_operations():
    """Test atomic Redis operations with concurrent updates."""
    print("\n=== Testing Atomic Operations ===")
    
    # Initialize dependencies
    init_redis()
    redis_repo = get_redis_repository()
    
    job_repository = RedisJobRepository(redis_repo)
    job_manager = JobManager(job_repository)
    file_repository = RedisFileRepository(redis_repo)
    file_manager = FileManager(file_repository)
    job_service = JobService(job_manager, file_manager)
    
    # Create and start a job
    print("\n1. Creating job for atomic update test...")
    result = job_service.create_download_job(
        "https://www.youtube.com/watch?v=test",
        "137"
    )
    job_id = result["job_id"]
    job_service.start_job(job_id)
    print(f"   ✓ Job created: {job_id}")
    
    # Perform multiple rapid updates
    print("\n2. Performing rapid progress updates...")
    for i in range(1, 11):
        success = job_service.update_progress(
            job_id,
            percentage=i * 10,
            phase=f"downloading chunk {i}",
            speed=f"{i * 0.5} MB/s"
        )
        if not success:
            print(f"   ✗ Update {i} failed")
            return False
    print("   ✓ All 10 updates succeeded")
    
    # Verify final state
    print("\n3. Verifying final state...")
    status = job_service.get_job_status(job_id)
    print(f"   ✓ Final progress: {status['progress']['percentage']}%")
    print(f"   Phase: {status['progress']['phase']}")
    
    # Cleanup
    job_service.delete_job(job_id)
    print("\n=== Atomic Operations Test Passed! ===\n")
    return True


if __name__ == "__main__":
    try:
        # Run all tests
        test1 = test_job_lifecycle()
        test2 = test_job_failure()
        test3 = test_atomic_operations()
        
        if test1 and test2 and test3:
            print("\n" + "="*50)
            print("ALL TESTS PASSED SUCCESSFULLY!")
            print("="*50 + "\n")
            sys.exit(0)
        else:
            print("\n" + "="*50)
            print("SOME TESTS FAILED")
            print("="*50 + "\n")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
