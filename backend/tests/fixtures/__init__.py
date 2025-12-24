"""
Test fixtures package.

Provides factory functions, mock implementations, and assertion helpers for testing.
"""

from .domain_fixtures import (
    create_download_job,
    create_job_archive,
    create_downloaded_file,
    create_video_metadata,
    create_video_format,
)
from .value_object_fixtures import (
    create_youtube_url,
    create_youtube_url_string,
    create_invalid_youtube_url_string,
    create_format_id,
    create_invalid_format_id_string,
    create_download_token,
    create_valid_token_string,
    create_invalid_token_string,
    create_job_progress,
    create_progress_initial,
    create_progress_metadata_extraction,
    create_progress_downloading,
    create_progress_processing,
    create_progress_completed,
)
from .mock_repositories import (
    MockJobRepository,
    MockFileRepository,
    MockStorageRepository,
    MockMetadataExtractor,
    MockArchiveRepository,
)
from .assertion_helpers import (
    assert_job_equal,
    assert_archive_complete,
    assert_archive_from_job,
    assert_error_response,
    assert_websocket_event,
    assert_job_status,
    assert_job_is_terminal,
    assert_job_is_active,
    assert_timestamps_monotonic,
    assert_downloaded_file_valid,
    assert_progress_valid,
    assert_video_metadata_valid,
    assert_dict_contains_keys,
    assert_repository_called,
)

__all__ = [
    # Domain fixtures
    "create_download_job",
    "create_job_archive",
    "create_downloaded_file",
    "create_video_metadata",
    "create_video_format",
    # Value object fixtures
    "create_youtube_url",
    "create_youtube_url_string",
    "create_invalid_youtube_url_string",
    "create_format_id",
    "create_invalid_format_id_string",
    "create_download_token",
    "create_valid_token_string",
    "create_invalid_token_string",
    "create_job_progress",
    "create_progress_initial",
    "create_progress_metadata_extraction",
    "create_progress_downloading",
    "create_progress_processing",
    "create_progress_completed",
    # Mock repositories
    "MockJobRepository",
    "MockFileRepository",
    "MockStorageRepository",
    "MockMetadataExtractor",
    "MockArchiveRepository",
    # Assertion helpers
    "assert_job_equal",
    "assert_archive_complete",
    "assert_archive_from_job",
    "assert_error_response",
    "assert_websocket_event",
    "assert_job_status",
    "assert_job_is_terminal",
    "assert_job_is_active",
    "assert_timestamps_monotonic",
    "assert_downloaded_file_valid",
    "assert_progress_valid",
    "assert_video_metadata_valid",
    "assert_dict_contains_keys",
    "assert_repository_called",
]
