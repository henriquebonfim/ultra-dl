"""
Custom Assertion Helpers

Provides domain-specific assertion functions for cleaner test code.

Requirements: 7.4
"""

from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.job_management.entities import DownloadJob, JobArchive
from src.domain.job_management.value_objects import JobStatus


def assert_job_equal(
    actual: DownloadJob,
    expected: DownloadJob,
    ignore_timestamps: bool = False,
) -> None:
    """
    Assert two DownloadJob instances are equal.
    
    Performs deep equality check on all fields.
    
    Args:
        actual: The actual job to check
        expected: The expected job values
        ignore_timestamps: If True, skip timestamp comparison
        
    Raises:
        AssertionError: If jobs are not equal
    """
    assert actual.job_id == expected.job_id, \
        f"job_id mismatch: {actual.job_id} != {expected.job_id}"
    assert actual.url == expected.url, \
        f"url mismatch: {actual.url} != {expected.url}"
    assert str(actual.format_id) == str(expected.format_id), \
        f"format_id mismatch: {actual.format_id} != {expected.format_id}"
    assert actual.status == expected.status, \
        f"status mismatch: {actual.status} != {expected.status}"
    assert actual.progress.percentage == expected.progress.percentage, \
        f"progress.percentage mismatch: {actual.progress.percentage} != {expected.progress.percentage}"
    assert actual.progress.phase == expected.progress.phase, \
        f"progress.phase mismatch: {actual.progress.phase} != {expected.progress.phase}"
    assert actual.error_message == expected.error_message, \
        f"error_message mismatch: {actual.error_message} != {expected.error_message}"
    assert actual.error_category == expected.error_category, \
        f"error_category mismatch: {actual.error_category} != {expected.error_category}"
    assert actual.download_url == expected.download_url, \
        f"download_url mismatch: {actual.download_url} != {expected.download_url}"
    
    if not ignore_timestamps:
        assert actual.created_at == expected.created_at, \
            f"created_at mismatch: {actual.created_at} != {expected.created_at}"
        assert actual.updated_at == expected.updated_at, \
            f"updated_at mismatch: {actual.updated_at} != {expected.updated_at}"


def assert_archive_complete(archive: JobArchive) -> None:
    """
    Assert a JobArchive has all required fields populated.
    
    Validates that the archive contains complete metadata for audit purposes.
    
    Args:
        archive: The JobArchive to validate
        
    Raises:
        AssertionError: If any required field is missing or invalid
    """
    assert archive.job_id, "job_id is required"
    assert archive.url, "url is required"
    assert archive.format_id, "format_id is required"
    assert archive.status in ("completed", "failed"), \
        f"status must be 'completed' or 'failed', got '{archive.status}'"
    assert isinstance(archive.created_at, datetime), \
        f"created_at must be datetime, got {type(archive.created_at)}"
    assert isinstance(archive.archived_at, datetime), \
        f"archived_at must be datetime, got {type(archive.archived_at)}"
    
    # completed_at should be set for terminal jobs
    if archive.status == "completed":
        assert archive.completed_at is not None, \
            "completed_at is required for completed jobs"
    
    # error_message should be set for failed jobs
    if archive.status == "failed":
        assert archive.error_message is not None, \
            "error_message is required for failed jobs"


def assert_archive_from_job(archive: JobArchive, job: DownloadJob) -> None:
    """
    Assert a JobArchive was correctly created from a DownloadJob.
    
    Validates that all metadata was properly transferred from job to archive.
    
    Args:
        archive: The created JobArchive
        job: The source DownloadJob
        
    Raises:
        AssertionError: If archive doesn't match job metadata
    """
    assert archive.job_id == job.job_id, \
        f"job_id mismatch: {archive.job_id} != {job.job_id}"
    assert archive.url == job.url, \
        f"url mismatch: {archive.url} != {job.url}"
    assert archive.format_id == str(job.format_id), \
        f"format_id mismatch: {archive.format_id} != {job.format_id}"
    assert archive.status == job.status.value, \
        f"status mismatch: {archive.status} != {job.status.value}"
    assert archive.created_at == job.created_at, \
        f"created_at mismatch: {archive.created_at} != {job.created_at}"
    assert archive.error_message == job.error_message, \
        f"error_message mismatch: {archive.error_message} != {job.error_message}"
    assert archive.error_category == job.error_category, \
        f"error_category mismatch: {archive.error_category} != {job.error_category}"


def assert_error_response(
    response: Dict[str, Any],
    expected_error: str,
    expected_status: Optional[int] = None,
) -> None:
    """
    Assert an API error response has correct structure and values.
    
    Args:
        response: The error response dictionary
        expected_error: Expected error category value
        expected_status: Expected HTTP status code (if checking tuple response)
        
    Raises:
        AssertionError: If response structure or values are incorrect
    """
    assert "error" in response, "Response must contain 'error' field"
    assert "title" in response, "Response must contain 'title' field"
    assert "message" in response, "Response must contain 'message' field"
    assert "action" in response, "Response must contain 'action' field"
    
    assert response["error"] == expected_error, \
        f"error mismatch: {response['error']} != {expected_error}"
    
    # Validate field types
    assert isinstance(response["title"], str), "title must be a string"
    assert isinstance(response["message"], str), "message must be a string"
    assert isinstance(response["action"], str), "action must be a string"
    
    # Ensure user-friendly messages don't contain technical details
    assert "traceback" not in response["message"].lower(), \
        "Error message should not contain traceback"
    assert "exception" not in response["message"].lower(), \
        "Error message should not contain 'exception'"


def assert_websocket_event(
    event: Dict[str, Any],
    expected_type: str,
    expected_job_id: Optional[str] = None,
) -> None:
    """
    Assert a WebSocket event has correct structure and values.
    
    Args:
        event: The WebSocket event dictionary
        expected_type: Expected event type (e.g., "progress", "error", "completed")
        expected_job_id: Expected job ID in the event
        
    Raises:
        AssertionError: If event structure or values are incorrect
    """
    assert "type" in event or "event" in event, \
        "Event must contain 'type' or 'event' field"
    
    event_type = event.get("type") or event.get("event")
    assert event_type == expected_type, \
        f"event type mismatch: {event_type} != {expected_type}"
    
    if expected_job_id:
        job_id = event.get("job_id") or event.get("data", {}).get("job_id")
        assert job_id == expected_job_id, \
            f"job_id mismatch: {job_id} != {expected_job_id}"


def assert_job_status(job: DownloadJob, expected_status: JobStatus) -> None:
    """
    Assert a job has the expected status.
    
    Args:
        job: The job to check
        expected_status: Expected JobStatus value
        
    Raises:
        AssertionError: If status doesn't match
    """
    assert job.status == expected_status, \
        f"Job status mismatch: {job.status} != {expected_status}"


def assert_job_is_terminal(job: DownloadJob) -> None:
    """
    Assert a job is in a terminal state (completed or failed).
    
    Args:
        job: The job to check
        
    Raises:
        AssertionError: If job is not in terminal state
    """
    assert job.is_terminal(), \
        f"Job should be in terminal state, but is {job.status.value}"


def assert_job_is_active(job: DownloadJob) -> None:
    """
    Assert a job is in an active state (pending or processing).
    
    Args:
        job: The job to check
        
    Raises:
        AssertionError: If job is not in active state
    """
    assert job.is_active(), \
        f"Job should be in active state, but is {job.status.value}"


def assert_timestamps_monotonic(
    earlier: datetime,
    later: datetime,
    field_name: str = "timestamp",
) -> None:
    """
    Assert that timestamps are in monotonic order.
    
    Args:
        earlier: The timestamp that should be earlier
        later: The timestamp that should be later or equal
        field_name: Name of the field for error message
        
    Raises:
        AssertionError: If timestamps are not in order
    """
    assert earlier <= later, \
        f"{field_name} not monotonic: {earlier} should be <= {later}"



def assert_downloaded_file_valid(file: Any) -> None:
    """
    Assert a DownloadedFile entity has all required fields.
    
    Args:
        file: DownloadedFile entity to validate
        
    Raises:
        AssertionError: If any required field is missing or invalid
    """
    assert file.file_path, "file_path is required"
    assert file.token, "token is required"
    assert file.job_id, "job_id is required"
    assert file.filename, "filename is required"
    assert isinstance(file.expires_at, datetime), \
        f"expires_at must be datetime, got {type(file.expires_at)}"
    assert isinstance(file.created_at, datetime), \
        f"created_at must be datetime, got {type(file.created_at)}"
    
    # Token should be at least 32 characters
    assert len(str(file.token)) >= 32, \
        f"token must be at least 32 characters, got {len(str(file.token))}"


def assert_progress_valid(progress: Any) -> None:
    """
    Assert a JobProgress value object is valid.
    
    Args:
        progress: JobProgress to validate
        
    Raises:
        AssertionError: If progress is invalid
    """
    assert 0 <= progress.percentage <= 100, \
        f"percentage must be 0-100, got {progress.percentage}"
    assert progress.phase, "phase is required"
    
    if progress.eta is not None:
        assert progress.eta >= 0, f"eta must be non-negative, got {progress.eta}"


def assert_video_metadata_valid(metadata: Any) -> None:
    """
    Assert a VideoMetadata entity has all required fields.
    
    Args:
        metadata: VideoMetadata entity to validate
        
    Raises:
        AssertionError: If any required field is missing or invalid
    """
    assert metadata.id, "id is required"
    assert metadata.title, "title is required"
    assert metadata.uploader, "uploader is required"
    assert metadata.duration >= 0, \
        f"duration must be non-negative, got {metadata.duration}"
    assert metadata.thumbnail, "thumbnail is required"
    assert metadata.url, "url is required"


def assert_dict_contains_keys(
    data: Dict[str, Any],
    required_keys: list,
    context: str = "dictionary",
) -> None:
    """
    Assert a dictionary contains all required keys.
    
    Args:
        data: Dictionary to check
        required_keys: List of keys that must be present
        context: Context string for error messages
        
    Raises:
        AssertionError: If any required key is missing
    """
    missing = [key for key in required_keys if key not in data]
    assert not missing, \
        f"{context} is missing required keys: {missing}"


def assert_repository_called(
    mock_repo: Any,
    method_name: str,
    times: Optional[int] = None,
    with_args: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Assert a mock repository method was called.
    
    Args:
        mock_repo: Mock repository with call history
        method_name: Name of the method to check
        times: Expected number of calls (None = at least once)
        with_args: Expected arguments in at least one call
        
    Raises:
        AssertionError: If method was not called as expected
    """
    history = mock_repo.get_call_history()
    calls = [c for c in history if c["method"] == method_name]
    
    if times is not None:
        assert len(calls) == times, \
            f"Expected {method_name} to be called {times} times, got {len(calls)}"
    else:
        assert len(calls) > 0, \
            f"Expected {method_name} to be called at least once"
    
    if with_args is not None:
        matching = [
            c for c in calls
            if all(c["args"].get(k) == v for k, v in with_args.items())
        ]
        assert len(matching) > 0, \
            f"Expected {method_name} to be called with args {with_args}, " \
            f"but got calls: {[c['args'] for c in calls]}"
