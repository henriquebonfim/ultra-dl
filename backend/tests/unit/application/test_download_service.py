"""
Unit tests for DownloadService

Tests download orchestration with mocked dependencies, WebSocket progress event emission,
error handling and ApplicationError wrapping, and domain exception translation.

Requirements: 2.1, 2.2, 2.3
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from src.application.download_service import DownloadService
from src.domain.errors import (
    ErrorCategory,
)
from src.domain.file_storage.services import FileManager
from src.domain.job_management.services import JobManager
from src.domain.job_management.value_objects import JobStatus
from src.domain.video_processing.services import VideoProcessor

from tests.fixtures.domain_fixtures import create_download_job, create_downloaded_file
from tests.fixtures.mock_repositories import MockStorageRepository


@pytest.fixture
def mock_job_manager():
    """Mock JobManager for testing."""
    mock = Mock(spec=JobManager)
    mock.start_job.return_value = create_download_job(status=JobStatus.PROCESSING)
    mock.update_job_progress.return_value = True
    mock.complete_job.return_value = create_download_job(status=JobStatus.COMPLETED)
    mock.fail_job.return_value = create_download_job(status=JobStatus.FAILED)
    return mock


@pytest.fixture
def mock_file_manager():
    """Mock FileManager for testing."""
    mock = Mock(spec=FileManager)
    mock.register_file.return_value = create_downloaded_file()
    return mock


@pytest.fixture
def mock_video_processor():
    """Mock VideoProcessor for testing."""
    mock = Mock(spec=VideoProcessor)
    return mock


@pytest.fixture
def mock_storage_repository():
    """Mock storage repository for testing."""
    return MockStorageRepository()


@pytest.fixture
def download_service(
    mock_job_manager, mock_file_manager, mock_video_processor, mock_storage_repository
):
    """Create DownloadService with mocked dependencies."""
    return DownloadService(
        job_manager=mock_job_manager,
        file_manager=mock_file_manager,
        video_processor=mock_video_processor,
        storage_repository=mock_storage_repository,
    )


class TestDownloadServiceOrchestration:
    """Test download workflow orchestration."""

    @patch("src.application.download_service.YoutubeDL")
    @patch("src.application.download_service.emit_websocket_job_progress")
    @patch("src.application.download_service.emit_websocket_job_completed")
    def test_execute_download_success_workflow(
        self,
        mock_emit_completed,
        mock_emit_progress,
        mock_yt_dlp,
        download_service,
        mock_job_manager,
        mock_storage_repository,
        tmp_path,
    ):
        """
        Test successful download workflow orchestration.

        Verifies that:
        - Job is started
        - Video is downloaded with yt-dlp
        - File is stored to storage repository
        - Job is completed with download URL
        - WebSocket events are emitted
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Create a temporary file to simulate download
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test video content")

        # Mock yt-dlp behavior with progress hook simulation
        mock_ydl_instance = MagicMock()

        def mock_download(urls):
            # Simulate progress hook being called during download
            # The progress hook is captured in ydl_opts["progress_hooks"]
            # We need to trigger it manually in the test
            pass

        mock_ydl_instance.download = mock_download
        mock_ydl_instance.extract_info.return_value = {
            "title": "Test Video",
            "ext": "mp4",
        }
        mock_ydl_instance.prepare_filename.return_value = str(test_file)
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is True
        assert result.error_message is None

        # Verify job was started
        mock_job_manager.start_job.assert_called_once_with(job_id)

        # Verify yt-dlp was called
        mock_ydl_instance.extract_info.assert_called_once_with(url, download=False)

        # Verify file was stored
        assert len(mock_storage_repository.get_stored_content()) > 0

        # Verify job was completed
        mock_job_manager.complete_job.assert_called_once()

        # Verify WebSocket completion event was emitted
        mock_emit_completed.assert_called_once()

    @patch("src.application.download_service.YoutubeDL")
    @patch("src.application.download_service.emit_websocket_job_completed")
    @patch("src.application.download_service.emit_websocket_job_progress")
    def test_execute_download_with_trim_options(
        self,
        mock_emit_progress,
        mock_emit_completed,
        mock_yt_dlp,
        download_service,
        mock_job_manager,
        tmp_path,
    ):
        """
        Test execute_download with trimming options.

        Verifies that yt-dlp is configured with correct download_sections
        and postprocessors when start_time and end_time are provided.
        """
        # Arrange
        job_id = "test-job-trim"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"
        start_time = 10.0
        end_time = 20.0

        test_file = tmp_path / "test_video_trim.mp4"
        test_file.write_bytes(b"test video content")

        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {
            "title": "Test Trim",
            "ext": "mp4",
        }
        mock_ydl_instance.prepare_filename.return_value = str(test_file)

        # We need to capture the options passed to YoutubeDL constructor
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

        # Act
        result = download_service.execute_download(
            job_id, url, format_id, start_time=start_time, end_time=end_time
        )

        # Assert
        assert result.success is True

        # Verify call args for YoutubeDL constructor
        # call_args[0] are positional args, first one is params dict
        call_args = mock_yt_dlp.call_args
        params = call_args[0][0]

        assert params["download_sections"] == "*10.0-20.0"
        assert params["force_keyframes_at_cuts"] is True

        # Verify postprocessors
        postprocessors = params["postprocessors"]
        assert len(postprocessors) == 1
        assert postprocessors[0]["key"] == "FFmpegVideoConvertor"
        # Default format is 'webm' when format_str is not provided
        assert postprocessors[0]["preferedformat"] == "webm"

    @patch("src.application.download_service.YoutubeDL")
    def test_execute_download_calls_progress_callback(
        self, mock_yt_dlp, download_service, tmp_path
    ):
        """
        Test that progress callback is called during download.

        Verifies that external progress callbacks are invoked with
        JobProgress updates.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"
        progress_callback = Mock()

        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        # Mock yt-dlp to trigger progress hook
        mock_ydl_instance = MagicMock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Test", "ext": "mp4"}
        mock_ydl_instance.prepare_filename.return_value = str(test_file)

        # Capture progress hook and simulate progress
        def capture_hook(opts):
            progress_hook = opts["progress_hooks"][0]
            # Simulate downloading progress
            progress_hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 500,
                    "total_bytes": 1000,
                    "speed": 1024 * 100,  # 100 KB/s
                    "eta": 5,
                }
            )
            # Simulate finished
            progress_hook({"status": "finished"})

        mock_yt_dlp.side_effect = lambda opts: (
            capture_hook(opts),
            MagicMock(
                __enter__=lambda self: mock_ydl_instance, __exit__=lambda *args: None
            ),
        )[1]

        # Act
        result = download_service.execute_download(
            job_id, url, format_id, progress_callback=progress_callback
        )

        # Assert
        assert result.success is True
        # Progress callback should have been called
        assert progress_callback.called

    @patch("src.application.download_service.YoutubeDL")
    @patch("src.application.download_service.emit_websocket_job_progress")
    def test_execute_download_updates_progress(
        self,
        mock_emit_progress,
        mock_yt_dlp,
        download_service,
        mock_job_manager,
        tmp_path,
    ):
        """
        Test that job progress is updated during download.

        Verifies that JobManager.update_job_progress is called with
        appropriate progress values.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        mock_ydl_instance = MagicMock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Test", "ext": "mp4"}
        mock_ydl_instance.prepare_filename.return_value = str(test_file)

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is True
        # Verify progress was updated (at least for metadata extraction)
        assert mock_job_manager.update_job_progress.called


class TestDownloadServiceWebSocketEvents:
    """Test WebSocket event emission."""

    @patch("src.application.download_service.YoutubeDL")
    @patch("src.application.download_service.emit_websocket_job_progress")
    @patch("src.application.download_service.emit_websocket_job_completed")
    def test_emits_progress_events(
        self,
        mock_emit_completed,
        mock_emit_progress,
        mock_yt_dlp,
        download_service,
        tmp_path,
        mock_job_manager,
    ):
        """
        Test that WebSocket progress events are emitted.

        Verifies that emit_websocket_job_progress is called with
        correct job_id and progress information.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        # Capture the progress hook and simulate progress
        captured_hooks = []

        def mock_yt_dlp_init(opts):
            captured_hooks.extend(opts.get("progress_hooks", []))
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = {"title": "Test", "ext": "mp4"}
            mock_ydl.prepare_filename.return_value = str(test_file)

            def mock_download(urls):
                # Simulate progress during download
                for hook in captured_hooks:
                    hook(
                        {
                            "status": "downloading",
                            "downloaded_bytes": 500,
                            "total_bytes": 1000,
                        }
                    )
                    hook({"status": "finished"})

            mock_ydl.download = mock_download
            return MagicMock(
                __enter__=lambda self: mock_ydl, __exit__=lambda *args: None
            )

        mock_yt_dlp.side_effect = mock_yt_dlp_init

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is True
        # Verify progress events were emitted
        assert mock_emit_progress.called
        # Check that job_id was passed
        calls = mock_emit_progress.call_args_list
        for call_args in calls:
            assert call_args[0][0] == job_id  # First arg should be job_id

    @patch("src.application.download_service.YoutubeDL")
    @patch("src.application.download_service.emit_websocket_job_completed")
    def test_emits_completion_event(
        self, mock_emit_completed, mock_yt_dlp, download_service, tmp_path
    ):
        """
        Test that WebSocket completion event is emitted on success.

        Verifies that emit_websocket_job_completed is called with
        job_id, download_url, and expire_at.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        mock_ydl_instance = MagicMock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Test", "ext": "mp4"}
        mock_ydl_instance.prepare_filename.return_value = str(test_file)

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is True
        mock_emit_completed.assert_called_once()
        # Verify arguments
        call_args = mock_emit_completed.call_args[0]
        assert call_args[0] == job_id

    @patch("src.application.download_service.YoutubeDL")
    @patch("src.application.download_service.emit_websocket_job_failed")
    def test_emits_failure_event_on_error(
        self, mock_emit_failed, mock_yt_dlp, download_service
    ):
        """
        Test that WebSocket failure event is emitted on error.

        Verifies that emit_websocket_job_failed is called with
        job_id, error_message, and error_category.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise an error
        mock_yt_dlp.return_value.__enter__.side_effect = Exception("Download failed")

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        mock_emit_failed.assert_called_once()
        # Verify arguments
        call_args = mock_emit_failed.call_args[0]
        assert call_args[0] == job_id
        assert isinstance(call_args[1], str)  # error_message
        assert isinstance(call_args[2], str)  # error_category


class TestDownloadServiceErrorHandling:
    """Test error handling and categorization."""

    @patch("src.application.download_service.YoutubeDL")
    def test_handles_yt_dlp_download_error(
        self, mock_yt_dlp, download_service, mock_job_manager
    ):
        """
        Test handling of yt-dlp DownloadError.

        Verifies that DownloadError is caught, categorized, and
        job is marked as failed with appropriate error message.
        """
        # Arrange
        from yt_dlp.utils import DownloadError

        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise DownloadError
        mock_yt_dlp.return_value.__enter__.side_effect = DownloadError("HTTP Error 404")

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert result.error_type is not None

        # Verify job was marked as failed
        mock_job_manager.fail_job.assert_called_once()

    @patch("src.application.download_service.YoutubeDL")
    def test_handles_yt_dlp_unavailable_video_error(
        self, mock_yt_dlp, download_service, mock_job_manager
    ):
        """
        Test handling of yt-dlp UnavailableVideoError.

        Verifies that UnavailableVideoError is categorized as
        VIDEO_UNAVAILABLE.
        """
        # Arrange
        from yt_dlp.utils import UnavailableVideoError

        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise UnavailableVideoError
        mock_yt_dlp.return_value.__enter__.side_effect = UnavailableVideoError(
            "Video unavailable"
        )

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_type == ErrorCategory.VIDEO_UNAVAILABLE.value

    @patch("src.application.download_service.YoutubeDL")
    def test_handles_yt_dlp_extractor_error(
        self, mock_yt_dlp, download_service, mock_job_manager
    ):
        """
        Test handling of yt-dlp ExtractorError.

        Verifies that ExtractorError is caught and categorized
        appropriately based on error message.
        """
        # Arrange
        from yt_dlp.utils import ExtractorError

        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise ExtractorError
        mock_yt_dlp.return_value.__enter__.side_effect = ExtractorError(
            "Unsupported URL"
        )

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_type == ErrorCategory.INVALID_URL.value

    @patch("src.application.download_service.YoutubeDL")
    def test_handles_generic_exception(
        self, mock_yt_dlp, download_service, mock_job_manager
    ):
        """
        Test handling of generic exceptions.

        Verifies that unexpected exceptions are caught and
        categorized as SYSTEM_ERROR.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise generic exception
        mock_yt_dlp.return_value.__enter__.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_type == ErrorCategory.SYSTEM_ERROR.value

    @patch("src.application.download_service.YoutubeDL")
    def test_error_categorization_geo_blocked(self, mock_yt_dlp, download_service):
        """
        Test error categorization for geo-blocked content.

        Verifies that errors containing geo-blocking indicators
        are categorized as GEO_BLOCKED.
        """
        # Arrange
        from yt_dlp.utils import DownloadError

        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise geo-blocking error
        mock_yt_dlp.return_value.__enter__.side_effect = DownloadError(
            "HTTP Error 403: This video is not available in your region"
        )

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_type == ErrorCategory.GEO_BLOCKED.value

    @patch("src.application.download_service.YoutubeDL")
    def test_error_categorization_login_required(self, mock_yt_dlp, download_service):
        """
        Test error categorization for login-required content.

        Verifies that errors indicating login requirement
        are categorized as LOGIN_REQUIRED.
        """
        # Arrange
        from yt_dlp.utils import DownloadError

        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise login required error
        mock_yt_dlp.return_value.__enter__.side_effect = DownloadError(
            "HTTP Error 403: Please sign in to view this video"
        )

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_type == ErrorCategory.LOGIN_REQUIRED.value

    @patch("src.application.download_service.YoutubeDL")
    def test_error_categorization_rate_limited(self, mock_yt_dlp, download_service):
        """
        Test error categorization for platform rate limiting.

        Verifies that 429 errors are categorized as
        PLATFORM_RATE_LIMITED.
        """
        # Arrange
        from yt_dlp.utils import DownloadError

        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        # Mock yt-dlp to raise rate limit error
        mock_yt_dlp.return_value.__enter__.side_effect = DownloadError(
            "HTTP Error 429: Too many requests"
        )

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is False
        assert result.error_type == ErrorCategory.PLATFORM_RATE_LIMITED.value


class TestDownloadServiceFileStorage:
    """Test file storage operations."""

    @patch("src.application.download_service.YoutubeDL")
    def test_stores_file_to_storage_repository(
        self, mock_yt_dlp, download_service, mock_storage_repository, tmp_path
    ):
        """
        Test that downloaded file is stored to storage repository.

        Verifies that storage_repository.save is called with
        correct file path and content.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        test_file = tmp_path / "test_video.mp4"
        test_content = b"test video content"
        test_file.write_bytes(test_content)

        mock_ydl_instance = MagicMock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Test", "ext": "mp4"}
        mock_ydl_instance.prepare_filename.return_value = str(test_file)

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is True
        # Verify file was stored
        stored_content = mock_storage_repository.get_stored_content()
        assert len(stored_content) > 0
        # Verify content matches
        stored_file_content = list(stored_content.values())[0]
        assert stored_file_content == test_content

    @patch("src.application.download_service.YoutubeDL")
    def test_generates_local_download_url(
        self, mock_yt_dlp, download_service, mock_file_manager, tmp_path
    ):
        """
        Test that local download URL is generated by registering the file.

        Verifies that FileManager.register_file is called and a download URL is
        generated from the registered file.
        """
        # Arrange
        job_id = "test-job-123"
        url = "https://www.youtube.com/watch?v=test"
        format_id = "best"

        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        mock_ydl_instance = MagicMock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Test", "ext": "mp4"}
        mock_ydl_instance.prepare_filename.return_value = str(test_file)

        # Mock registered file
        mock_registered_file = create_downloaded_file()
        mock_registered_file.generate_download_url = Mock(
            return_value="http://localhost/api/v1/downloads/file/test-token"
        )
        mock_file_manager.register_file.return_value = mock_registered_file

        # Act
        result = download_service.execute_download(job_id, url, format_id)

        # Assert
        assert result.success is True
        # Verify file was registered
        mock_file_manager.register_file.assert_called_once()

    def test_sanitizes_filename(self, download_service):
        """
        Test that filenames are sanitized for safe storage.

        Verifies that unsafe characters are removed from filenames.
        """
        # Test various unsafe filenames
        assert download_service._sanitize_filename("test/file.mp4") == "testfile.mp4"
        assert download_service._sanitize_filename("test\\file.mp4") == "testfile.mp4"
        assert download_service._sanitize_filename("test:file.mp4") == "testfile.mp4"
        assert download_service._sanitize_filename("test*file.mp4") == "testfile.mp4"
        assert download_service._sanitize_filename("") == "download"
        assert (
            download_service._sanitize_filename("normal_file.mp4") == "normal_file.mp4"
        )
