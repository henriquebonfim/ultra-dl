from datetime import datetime

from src.domain.events import (
    FormatExtractionCompletedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent,
    JobStartedEvent,
    MetadataExtractionFailedEvent,
    VideoDownloadCompletedEvent,
    VideoDownloadFailedEvent,
    VideoDownloadProgressEvent,
    VideoDownloadStartedEvent,
    VideoMetadataExtractedEvent,
)
from src.domain.job_management.value_objects import JobProgress


def test_all_events_to_dict_cover_fields():
    now = datetime.utcnow()
    prog = JobProgress.processing(10)

    cases = [
        JobStartedEvent(aggregate_id="job1", occurred_at=now, url="u", format_id="f"),
        JobProgressUpdatedEvent(aggregate_id="job1", occurred_at=now, progress=prog),
        JobCompletedEvent(
            aggregate_id="job1", occurred_at=now, download_url="/d", expire_at=now
        ),
        JobFailedEvent(
            aggregate_id="job1",
            occurred_at=now,
            error_message="err",
            error_category="system",
        ),
        VideoMetadataExtractedEvent(
            aggregate_id="job1", occurred_at=now, video_id="vid", title="t", duration=1
        ),
        MetadataExtractionFailedEvent(
            aggregate_id="job1", occurred_at=now, url="u", error_message="e"
        ),
        FormatExtractionCompletedEvent(
            aggregate_id="job1", occurred_at=now, url="u", format_count=3
        ),
        VideoDownloadStartedEvent(
            aggregate_id="job1", occurred_at=now, video_id="vid", format_id="f"
        ),
        VideoDownloadProgressEvent(
            aggregate_id="job1",
            occurred_at=now,
            video_id="vid",
            downloaded_bytes=10,
            total_bytes=100,
            percentage=10.0,
        ),
        VideoDownloadCompletedEvent(
            aggregate_id="job1",
            occurred_at=now,
            video_id="vid",
            file_path="/tmp/f",
            file_size=123,
        ),
        VideoDownloadFailedEvent(
            aggregate_id="job1", occurred_at=now, video_id="vid", error_message="e"
        ),
    ]

    for ev in cases:
        d = ev.to_dict()
        assert d["event_type"] == ev.__class__.__name__
        assert d["aggregate_id"] == "job1"
        assert "occurred_at" in d
