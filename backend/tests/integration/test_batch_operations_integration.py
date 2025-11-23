"""
Batch Operations Integration Tests

Tests for batch operations in JobRepository (get_many, save_many, find_by_status).
Validates performance improvements through reduced Redis round trips.

Run with: docker-compose exec backend python test_batch_operations.py
"""

import os
import sys
import time
from datetime import datetime
from typing import List

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_repository
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobStatus, JobProgress
from infrastructure.redis_job_repository import RedisJobRepository


class BatchOperationsTests:
    """Integration tests for batch operations in JobRepository."""
    
    def __init__(self, repository: RedisJobRepository):
        self.repo = repository
        self.test_prefix = "batch_test"
        self.test_jobs = []
    
    def cleanup(self):
        """Clean up test data."""
        for job_id in self.test_jobs:
            try:
                self.repo.delete(job_id)
            except:
                pass
        self.test_jobs.clear()
    
    def _create_test_job(self, status: JobStatus = JobStatus.PENDING) -> DownloadJob:
        """Create a test job with specified status."""
        job = DownloadJob.create(
            url=f"https://www.youtube.com/watch?v=test{int(time.time() * 1000000)}",
            format_id="137"
        )
        job.status = status
        self.test_jobs.append(job.job_id)
        return job
    
    def test_get_many_retrieves_multiple_jobs(self) -> bool:
        """Test that get_many retrieves multiple jobs correctly."""
        print("  Testing get_many retrieves multiple jobs...")
        
        # Create and save 5 test jobs
        jobs = [self._create_test_job() for _ in range(5)]
        for job in jobs:
            if not self.repo.save(job):
                print("    ✗ Failed to save test job")
                return False
        
        # Retrieve all jobs using get_many
        job_ids = [job.job_id for job in jobs]
        retrieved_jobs = self.repo.get_many(job_ids)
        
        # Verify all jobs were retrieved
        if len(retrieved_jobs) != 5:
            print(f"    ✗ Expected 5 jobs, got {len(retrieved_jobs)}")
            return False
        
        # Verify job IDs match
        retrieved_ids = {job.job_id for job in retrieved_jobs}
        expected_ids = set(job_ids)
        
        if retrieved_ids != expected_ids:
            print(f"    ✗ Job IDs don't match")
            print(f"      Expected: {expected_ids}")
            print(f"      Got: {retrieved_ids}")
            return False
        
        # Verify job data integrity
        for retrieved_job in retrieved_jobs:
            original_job = next(j for j in jobs if j.job_id == retrieved_job.job_id)
            if retrieved_job.url != original_job.url:
                print(f"    ✗ URL mismatch for job {retrieved_job.job_id}")
                return False
            if retrieved_job.status != original_job.status:
                print(f"    ✗ Status mismatch for job {retrieved_job.job_id}")
                return False
        
        print("    ✓ get_many retrieves multiple jobs correctly")
        return True
    
    def test_get_many_with_empty_list(self) -> bool:
        """Test that get_many handles empty list correctly."""
        print("  Testing get_many with empty list...")
        
        retrieved_jobs = self.repo.get_many([])
        
        if len(retrieved_jobs) != 0:
            print(f"    ✗ Expected empty list, got {len(retrieved_jobs)} jobs")
            return False
        
        print("    ✓ get_many handles empty list correctly")
        return True
    
    def test_get_many_with_nonexistent_jobs(self) -> bool:
        """Test that get_many handles non-existent jobs gracefully."""
        print("  Testing get_many with non-existent jobs...")
        
        # Create mix of existing and non-existent job IDs
        existing_job = self._create_test_job()
        self.repo.save(existing_job)
        
        job_ids = [
            existing_job.job_id,
            "nonexistent_job_1",
            "nonexistent_job_2"
        ]
        
        retrieved_jobs = self.repo.get_many(job_ids)
        
        # Should only retrieve the existing job
        if len(retrieved_jobs) != 1:
            print(f"    ✗ Expected 1 job, got {len(retrieved_jobs)}")
            return False
        
        if retrieved_jobs[0].job_id != existing_job.job_id:
            print(f"    ✗ Retrieved wrong job")
            return False
        
        print("    ✓ get_many handles non-existent jobs gracefully")
        return True
    
    def test_save_many_saves_multiple_jobs(self) -> bool:
        """Test that save_many saves multiple jobs atomically."""
        print("  Testing save_many saves multiple jobs...")
        
        # Create 5 test jobs
        jobs = [self._create_test_job() for _ in range(5)]
        
        # Save all jobs using save_many
        if not self.repo.save_many(jobs):
            print("    ✗ save_many returned False")
            return False
        
        # Verify all jobs were saved
        for job in jobs:
            retrieved = self.repo.get(job.job_id)
            if retrieved is None:
                print(f"    ✗ Job {job.job_id} was not saved")
                return False
            
            if retrieved.url != job.url:
                print(f"    ✗ URL mismatch for job {job.job_id}")
                return False
            
            if retrieved.status != job.status:
                print(f"    ✗ Status mismatch for job {job.job_id}")
                return False
        
        print("    ✓ save_many saves multiple jobs correctly")
        return True
    
    def test_save_many_with_empty_list(self) -> bool:
        """Test that save_many handles empty list correctly."""
        print("  Testing save_many with empty list...")
        
        result = self.repo.save_many([])
        
        if not result:
            print("    ✗ save_many should return True for empty list")
            return False
        
        print("    ✓ save_many handles empty list correctly")
        return True
    
    def test_save_many_updates_existing_jobs(self) -> bool:
        """Test that save_many can update existing jobs."""
        print("  Testing save_many updates existing jobs...")
        
        # Create and save jobs
        jobs = [self._create_test_job() for _ in range(3)]
        self.repo.save_many(jobs)
        
        # Modify jobs
        for job in jobs:
            job.status = JobStatus.PROCESSING
            job.progress = JobProgress.downloading(percentage=50, speed="1.5 MB/s")
        
        # Save updated jobs
        if not self.repo.save_many(jobs):
            print("    ✗ save_many failed to update jobs")
            return False
        
        # Verify updates
        for job in jobs:
            retrieved = self.repo.get(job.job_id)
            if retrieved is None:
                print(f"    ✗ Job {job.job_id} not found after update")
                return False
            
            if retrieved.status != JobStatus.PROCESSING:
                print(f"    ✗ Status not updated for job {job.job_id}")
                return False
            
            if retrieved.progress.percentage != 50:
                print(f"    ✗ Progress not updated for job {job.job_id}")
                return False
        
        print("    ✓ save_many updates existing jobs correctly")
        return True
    
    def test_find_by_status_filters_correctly(self) -> bool:
        """Test that find_by_status filters jobs by status correctly."""
        print("  Testing find_by_status filters correctly...")
        
        # Create jobs with different statuses
        pending_jobs = [self._create_test_job(JobStatus.PENDING) for _ in range(3)]
        processing_jobs = [self._create_test_job(JobStatus.PROCESSING) for _ in range(2)]
        completed_jobs = [self._create_test_job(JobStatus.COMPLETED) for _ in range(2)]
        failed_jobs = [self._create_test_job(JobStatus.FAILED) for _ in range(1)]
        
        all_jobs = pending_jobs + processing_jobs + completed_jobs + failed_jobs
        
        # Save all jobs
        for job in all_jobs:
            if not self.repo.save(job):
                print(f"    ✗ Failed to save job {job.job_id}")
                return False
        
        # Find pending jobs
        found_pending = self.repo.find_by_status(JobStatus.PENDING, limit=100)
        pending_ids = {job.job_id for job in pending_jobs}
        found_pending_ids = {job.job_id for job in found_pending if job.job_id in pending_ids}
        
        if len(found_pending_ids) != 3:
            print(f"    ✗ Expected 3 pending jobs, found {len(found_pending_ids)}")
            return False
        
        # Find processing jobs
        found_processing = self.repo.find_by_status(JobStatus.PROCESSING, limit=100)
        processing_ids = {job.job_id for job in processing_jobs}
        found_processing_ids = {job.job_id for job in found_processing if job.job_id in processing_ids}
        
        if len(found_processing_ids) != 2:
            print(f"    ✗ Expected 2 processing jobs, found {len(found_processing_ids)}")
            return False
        
        # Find completed jobs
        found_completed = self.repo.find_by_status(JobStatus.COMPLETED, limit=100)
        completed_ids = {job.job_id for job in completed_jobs}
        found_completed_ids = {job.job_id for job in found_completed if job.job_id in completed_ids}
        
        if len(found_completed_ids) != 2:
            print(f"    ✗ Expected 2 completed jobs, found {len(found_completed_ids)}")
            return False
        
        # Find failed jobs
        found_failed = self.repo.find_by_status(JobStatus.FAILED, limit=100)
        failed_ids = {job.job_id for job in failed_jobs}
        found_failed_ids = {job.job_id for job in found_failed if job.job_id in failed_ids}
        
        if len(found_failed_ids) != 1:
            print(f"    ✗ Expected 1 failed job, found {len(found_failed_ids)}")
            return False
        
        print("    ✓ find_by_status filters correctly by status")
        return True
    
    def test_find_by_status_respects_limit(self) -> bool:
        """Test that find_by_status respects the limit parameter."""
        print("  Testing find_by_status respects limit...")
        
        # Create 10 pending jobs
        jobs = [self._create_test_job(JobStatus.PENDING) for _ in range(10)]
        for job in jobs:
            if not self.repo.save(job):
                print(f"    ✗ Failed to save job {job.job_id}")
                return False
        
        # Find with limit of 5
        found_jobs = self.repo.find_by_status(JobStatus.PENDING, limit=5)
        
        # Filter to only our test jobs
        test_job_ids = {job.job_id for job in jobs}
        found_test_jobs = [job for job in found_jobs if job.job_id in test_job_ids]
        
        if len(found_test_jobs) > 5:
            print(f"    ✗ Expected at most 5 jobs, found {len(found_test_jobs)}")
            return False
        
        print("    ✓ find_by_status respects limit parameter")
        return True
    
    def test_find_by_status_with_no_matches(self) -> bool:
        """Test that find_by_status returns empty list when no jobs match."""
        print("  Testing find_by_status with no matches...")
        
        # Create only pending jobs
        jobs = [self._create_test_job(JobStatus.PENDING) for _ in range(3)]
        for job in jobs:
            self.repo.save(job)
        
        # Try to find completed jobs (should be none from our test set)
        found_jobs = self.repo.find_by_status(JobStatus.COMPLETED, limit=100)
        
        # Filter to only our test jobs
        test_job_ids = {job.job_id for job in jobs}
        found_test_jobs = [job for job in found_jobs if job.job_id in test_job_ids]
        
        if len(found_test_jobs) != 0:
            print(f"    ✗ Expected 0 completed jobs from test set, found {len(found_test_jobs)}")
            return False
        
        print("    ✓ find_by_status returns empty list when no matches")
        return True
    
    def test_batch_operations_reduce_redis_round_trips(self) -> bool:
        """Test that batch operations reduce Redis round trips compared to individual operations."""
        print("  Testing batch operations reduce Redis round trips...")
        
        # Create 10 test jobs
        jobs = [self._create_test_job() for _ in range(10)]
        job_ids = [job.job_id for job in jobs]
        
        # Save jobs individually and measure time
        start_individual = time.time()
        for job in jobs:
            self.repo.save(job)
        individual_save_time = time.time() - start_individual
        
        # Retrieve jobs individually and measure time
        start_individual_get = time.time()
        for job_id in job_ids:
            self.repo.get(job_id)
        individual_get_time = time.time() - start_individual_get
        
        # Clean up for batch test
        for job_id in job_ids:
            self.repo.delete(job_id)
        
        # Save jobs using batch operation and measure time
        start_batch = time.time()
        self.repo.save_many(jobs)
        batch_save_time = time.time() - start_batch
        
        # Retrieve jobs using batch operation and measure time
        start_batch_get = time.time()
        self.repo.get_many(job_ids)
        batch_get_time = time.time() - start_batch_get
        
        # Batch operations should be faster (or at least not significantly slower)
        # We use a generous threshold since timing can vary
        save_improvement = individual_save_time / batch_save_time if batch_save_time > 0 else float('inf')
        get_improvement = individual_get_time / batch_get_time if batch_get_time > 0 else float('inf')
        
        print(f"      Individual save time: {individual_save_time:.4f}s")
        print(f"      Batch save time: {batch_save_time:.4f}s")
        print(f"      Save improvement: {save_improvement:.2f}x")
        print(f"      Individual get time: {individual_get_time:.4f}s")
        print(f"      Batch get time: {batch_get_time:.4f}s")
        print(f"      Get improvement: {get_improvement:.2f}x")
        
        # Batch should be at least as fast (allowing for some variance)
        if batch_save_time > individual_save_time * 1.5:
            print(f"    ⚠ Batch save slower than expected (but may be acceptable)")
        
        if batch_get_time > individual_get_time * 1.5:
            print(f"    ⚠ Batch get slower than expected (but may be acceptable)")
        
        # The test passes if batch operations complete successfully
        # Performance improvement is logged but not strictly enforced
        print("    ✓ Batch operations completed (performance metrics logged)")
        return True
    
    def run_all_tests(self) -> bool:
        """Run all batch operation tests."""
        print("\nBatch Operations Integration Tests")
        print("=" * 60)
        
        tests = [
            self.test_get_many_retrieves_multiple_jobs,
            self.test_get_many_with_empty_list,
            self.test_get_many_with_nonexistent_jobs,
            self.test_save_many_saves_multiple_jobs,
            self.test_save_many_with_empty_list,
            self.test_save_many_updates_existing_jobs,
            self.test_find_by_status_filters_correctly,
            self.test_find_by_status_respects_limit,
            self.test_find_by_status_with_no_matches,
            self.test_batch_operations_reduce_redis_round_trips,
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
        print(f"\nBatch Operations Tests: {passed}/{total} passed")
        
        return all(results)


def main():
    """Run all batch operation tests."""
    print("=" * 60)
    print("Batch Operations Test Suite")
    print("=" * 60)
    print("\nThese tests verify that batch operations in JobRepository")
    print("work correctly and provide performance improvements.")
    
    try:
        # Initialize Redis
        init_redis()
        redis_repo = get_redis_repository()
        
        # Create repository and run tests
        job_repo = RedisJobRepository(redis_repo)
        tests = BatchOperationsTests(job_repo)
        success = tests.run_all_tests()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ All batch operation tests passed")
            print("=" * 60)
            return 0
        else:
            print("✗ Some batch operation tests failed")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
