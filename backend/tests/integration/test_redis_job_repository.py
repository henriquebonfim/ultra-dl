
import pytest
from datetime import datetime, timedelta
import json
import time

from src.infrastructure.redis_job_repository import RedisJobRepository
from src.infrastructure.redis_repository import RedisRepository, RedisConnectionManager
from src.domain.job_management.entities import DownloadJob
from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.video_processing.value_objects import FormatId

@pytest.mark.integration
class TestRedisJobRepositoryIntegration:
    """Integration tests for RedisJobRepository using real Redis."""

    @pytest.fixture
    def redis_repo(self, redis_client):
        """Create RedisRepository instance using the fixture client."""
        # We need to wrap the redis_client in a way that RedisRepository expects,
        # or use internal logic. RedisJobRepository expects a RedisRepository instance.

        # RedisRepository expects a client, not a connection manager in its constructor
        base_repo = RedisRepository(redis_client, key_prefix="test_ultra_dl")
        return RedisJobRepository(base_repo)

    def test_save_and_get_job(self, redis_repo):
        """Verify full save and retrieval cycle works with Redis."""
        # Arrange
        job_id = "integration-test-job-1"
        now = datetime.utcnow()
        job = DownloadJob(
            job_id=job_id,
            url="https://youtube.com/watch?v=integration1",
            format_id=FormatId("best"),
            status=JobStatus.PENDING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now
        )

        # Act
        save_result = redis_repo.save(job)
        retrieved_job = redis_repo.get(job_id)

        # Assert
        assert save_result is True
        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.url == job.url
        assert retrieved_job.status == JobStatus.PENDING

    def test_update_progress_atomic(self, redis_repo):
        """Verify atomic progress updates using Lua scripts."""
        # Arrange
        job_id = "integration-test-job-2"
        now = datetime.utcnow()
        job = DownloadJob(
            job_id=job_id,
            url="https://youtube.com/watch?v=integration2",
            format_id=FormatId("best"),
            status=JobStatus.PROCESSING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now
        )
        redis_repo.save(job)

        # Act
        new_progress = JobProgress.downloading(
            percentage=45.5,
            speed="2.5 MB/s",
            eta=120
        )
        update_result = redis_repo.update_progress(job_id, new_progress)

        # Assert
        assert update_result is True

        # Verify persistence
        updated_job = redis_repo.get(job_id)
        assert updated_job.progress.percentage == 45.5
        assert updated_job.progress.phase == "downloading"
        assert updated_job.progress.speed == "2.5 MB/s"

    def test_find_by_status(self, redis_repo):
        """Verify finding jobs by status using SCAN."""
        # Arrange
        now = datetime.utcnow()
        job_completed = DownloadJob(
            job_id="job_completed_1",
            url="https://example.com/1",
            format_id=FormatId("best"),
            status=JobStatus.COMPLETED,
            progress=JobProgress.completed(),
            created_at=now,
            updated_at=now
        )
        job_pending = DownloadJob(
            job_id="job_pending_1",
            url="https://example.com/2",
            format_id=FormatId("best"),
            status=JobStatus.PENDING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now
        )

        redis_repo.save(job_completed)
        redis_repo.save(job_pending)

        # Act
        completed_jobs = redis_repo.find_by_status(JobStatus.COMPLETED)

        # Assert
        assert len(completed_jobs) == 1
        assert completed_jobs[0].job_id == "job_completed_1"

    def test_job_expiration(self, redis_repo):
        """Verify Redis TTL expires the job key."""
        # Arrange
        # Force a short TTL for testing
        redis_repo.ttl = 1  # 1 second

        job_id = "job_fast_expire"
        now = datetime.utcnow()
        job = DownloadJob(
            job_id=job_id,
            url="https://example.com/expire",
            format_id=FormatId("best"),
            status=JobStatus.PENDING,
            progress=JobProgress.initial(),
            created_at=now,
            updated_at=now
        )

        # Act
        redis_repo.save(job)
        assert redis_repo.get(job_id) is not None

        # Wait for expiration
        time.sleep(1.1)

        # Assert
        assert redis_repo.get(job_id) is None
