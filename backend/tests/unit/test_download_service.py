"""
Unit Tests for Download Service

Tests the DownloadService application service for video download orchestration.
Requirements: 9.4
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call

from application.download_service import DownloadService
from application.download_result import DownloadResult
from domain.errors import ErrorCategory
from domain.events import (
    JobStartedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent
)
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobProgress
from yt_dlp.utils import UnavailableVideoError, DownloadError


def create_mock_dependencies():
    """Create all mock dependencies for DownloadService."""
    job_manager = Mock()
    job = DownloadJob.create("https://youtube.com/watch?v=test", "137+140")
    job.job_id = "job-123"
    job_manager.start_job.return_value = job
    job_manager.update_job_progress.return_value = True
    job_manager.complete_job.return_value = job
    job_manager.fail_job.return_value = job
    
    file_manager = Mock()
    registered_file = Mock()
    registered_file.token = "test-token-123"
    registered_file.expires_at = datetime.utcnow() + timedelta(minutes=10)
    file_manager.register_file.return_value = registered_file
    
    video_processor = Mock()
    
    # Mock IFileStorageRepository instead of StorageService
    storage_repository = Mock()
    storage_repository.save.return_value = True
    storage_repository.exists.return_value = True
    storage_repository.get_size.return_value = 1024000
    
    event_publisher = Mock()
    
    return job_manager, file_manager, video_processor, storage_repository, event_publisher


class TestDownloadServiceSuccessWorkflow(unittest.TestCase):
    """Test successful download workflow."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_execute_download_success(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test successful download workflow with all steps.
        
        Note: SignedUrlService mock removed as it doesn't exist in production code.
        Download URL generation is handled by FileManager.register_file().
        """
        # Setup mocks
        job_manager, file_manager, video_processor, storage_repository, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            # For the final downloaded file check, return a mock that exists
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            # For directory operations, use real Path
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.download_url)
        self.assertIsNone(result.error_category)
        self.assertIsNone(result.error_message)
        
        # Verify job manager calls
        job_manager.start_job.assert_called_once_with("job-123")
        job_manager.complete_job.assert_called_once()
        
        # Verify storage service called
        storage_service.save_file.assert_called_once()
        
        # Verify file manager called for local storage
        file_manager.register_file.assert_called_once()
        
        # Verify events published
        self.assertGreaterEqual(event_publisher.publish.call_count, 2)  # At least JobStarted and JobCompleted
        
        # Verify JobStartedEvent published
        started_event_call = event_publisher.publish.call_args_list[0]
        started_event = started_event_call[0][0]
        self.assertIsInstance(started_event, JobStartedEvent)
        self.assertEqual(started_event.aggregate_id, "job-123")
        self.assertEqual(started_event.url, "https://youtube.com/watch?v=test")
        self.assertEqual(started_event.format_id, "137+140")
        
        # Verify JobCompletedEvent published (last call)
        completed_event_call = event_publisher.publish.call_args_list[-1]
        completed_event = completed_event_call[0][0]
        self.assertIsInstance(completed_event, JobCompletedEvent)
        self.assertEqual(completed_event.aggregate_id, "job-123")
        self.assertIsNotNone(completed_event.download_url)


class TestDownloadServiceErrorHandling(unittest.TestCase):
    """Test error handling and categorization."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_execute_download_unavailable_video(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test error handling for unavailable video."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise UnavailableVideoError
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = UnavailableVideoError("Video unavailable")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.VIDEO_UNAVAILABLE)
        self.assertIsNotNone(result.error_message)
        
        # Verify job manager calls
        job_manager.start_job.assert_called_once_with("job-123")
        job_manager.fail_job.assert_called_once()
        
        # Verify JobFailedEvent published
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.aggregate_id, "job-123")
        self.assertEqual(failed_event.error_category, ErrorCategory.VIDEO_UNAVAILABLE.value)
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_execute_download_system_error(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test error handling for system errors."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise generic exception
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = Exception("Unexpected error")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.SYSTEM_ERROR)
        self.assertIsNotNone(result.error_message)
        
        # Verify job failed
        job_manager.fail_job.assert_called_once()
        
        # Verify JobFailedEvent published
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.error_category, ErrorCategory.SYSTEM_ERROR.value)


class TestDownloadServiceEventPublishing(unittest.TestCase):
    """Test event publishing at each step."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_events_published_in_order(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test that events are published in correct order.
        
        Note: SignedUrlService mock removed as it doesn't exist in production code.
        Download URL generation is handled by FileManager.register_file().
        """
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            # For the final downloaded file check, return a mock that exists
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            # For directory operations, use real Path
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify events published
        self.assertGreaterEqual(event_publisher.publish.call_count, 2)
        
        # First event should be JobStartedEvent
        first_event = event_publisher.publish.call_args_list[0][0][0]
        self.assertIsInstance(first_event, JobStartedEvent)
        
        # Last event should be JobCompletedEvent
        last_event = event_publisher.publish.call_args_list[-1][0][0]
        self.assertIsInstance(last_event, JobCompletedEvent)


class TestDownloadServiceProgressCallback(unittest.TestCase):
    """Test progress callback invocation."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_progress_callback_invoked(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test that progress callback is invoked during download.
        
        Note: SignedUrlService mock removed as it doesn't exist in production code.
        Download URL generation is handled by FileManager.register_file().
        """
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            # For the final downloaded file check, return a mock that exists
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            # For directory operations, use real Path
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL with progress hook
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        
        # Capture progress hook
        progress_hook = None
        def capture_hook(opts):
            nonlocal progress_hook
            progress_hook = opts.get('progress_hooks', [])[0]
            return mock_ydl_instance
        
        mock_youtubedl_class.side_effect = capture_hook
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Create progress callback mock
        progress_callback = Mock()
        
        # Execute download
        service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140",
            progress_callback=progress_callback
        )
        
        # Simulate progress update
        if progress_hook:
            progress_hook({
                'status': 'downloading',
                'downloaded_bytes': 5000000,
                'total_bytes': 10000000,
                'speed': 1024000,
                'eta': 5
            })
            
            # Verify progress callback was invoked
            self.assertGreaterEqual(progress_callback.call_count, 1)
            
            # Verify JobProgressUpdatedEvent published
            progress_events = [
                call[0][0] for call in event_publisher.publish.call_args_list
                if isinstance(call[0][0], JobProgressUpdatedEvent)
            ]
            self.assertGreaterEqual(len(progress_events), 1)


class TestDownloadServiceStorageErrorHandling(unittest.TestCase):
    """Test storage error handling and GCS fallback."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_store_file_handles_gcs_fallback_to_local(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _store_file handles GCS fallback to local storage."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Mock storage service to simulate GCS failure and fallback
        storage_service.save_file.return_value = ("/tmp/ultra-dl/job-123/test_video.mp4", False)
        storage_service.is_using_gcs.return_value = False
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result is successful (fallback worked)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.download_url)
        
        # Verify storage service was called
        storage_service.save_file.assert_called_once()
        
        # Verify file manager was called for local storage
        file_manager.register_file.assert_called_once()
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_execute_download_handles_storage_errors(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test execute_download handles storage errors correctly."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Mock storage service to raise error
        storage_service.save_file.side_effect = Exception("Storage service unavailable")
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates failure
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.SYSTEM_ERROR)
        self.assertIsNotNone(result.error_message)
        
        # Verify job was failed
        job_manager.fail_job.assert_called_once()
        
        # Verify JobFailedEvent published
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)


class TestDownloadServiceProgressUpdates(unittest.TestCase):
    """Test progress update handling during download."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_execute_download_updates_progress_during_download(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test execute_download updates progress during download."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL with progress hook
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        
        # Capture progress hook
        progress_hook = None
        def capture_hook(opts):
            nonlocal progress_hook
            progress_hook = opts.get('progress_hooks', [])[0]
            return mock_ydl_instance
        
        mock_youtubedl_class.side_effect = capture_hook
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Simulate progress updates
        if progress_hook:
            progress_hook({
                'status': 'downloading',
                'downloaded_bytes': 2500000,
                'total_bytes': 10000000,
                'speed': 512000,
                'eta': 15
            })
            
            # Verify job manager was called to update progress
            self.assertGreaterEqual(job_manager.update_job_progress.call_count, 1)
            
            # Verify JobProgressUpdatedEvent was published
            progress_events = [
                call[0][0] for call in event_publisher.publish.call_args_list
                if isinstance(call[0][0], JobProgressUpdatedEvent)
            ]
            self.assertGreaterEqual(len(progress_events), 1)


class TestDownloadServiceJobCancellation(unittest.TestCase):
    """Test job cancellation handling."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_execute_download_handles_job_cancellation(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test execute_download handles job cancellation gracefully."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise cancellation error
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("Download cancelled by user")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates failure
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_category)
        self.assertIsNotNone(result.error_message)
        
        # Verify job was failed
        job_manager.fail_job.assert_called_once()
        
        # Verify JobFailedEvent published
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)


class TestDownloadServiceCompleteJob(unittest.TestCase):
    """Test _complete_job publishes domain event."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_complete_job_publishes_domain_event(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _complete_job publishes JobCompletedEvent."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock Path to support both directory creation and file operations
        from pathlib import Path as RealPath
        
        def path_side_effect(arg):
            if isinstance(arg, str) and arg.endswith(".mp4"):
                mock_file = Mock()
                mock_file.exists.return_value = True
                mock_file.name = "test_video.mp4"
                mock_file.__str__ = Mock(return_value=arg)
                return mock_file
            return RealPath(arg)
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock YoutubeDL
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"title": "test_video"}
        mock_ydl_instance.prepare_filename.return_value = "/tmp/ultra-dl/job-123/test_video.mp4"
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result is successful
        self.assertTrue(result.success)
        
        # Verify JobCompletedEvent was published
        completed_events = [
            call[0][0] for call in event_publisher.publish.call_args_list
            if isinstance(call[0][0], JobCompletedEvent)
        ]
        self.assertEqual(len(completed_events), 1)
        
        # Verify event details
        completed_event = completed_events[0]
        self.assertEqual(completed_event.aggregate_id, "job-123")
        self.assertIsNotNone(completed_event.download_url)
        self.assertIsNotNone(completed_event.expire_at)


class TestDownloadServiceErrorCategorization(unittest.TestCase):
    """Test _handle_error categorizes errors correctly."""
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_handle_error_categorizes_network_errors(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _handle_error categorizes network errors correctly."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise network error
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("Network connection timeout")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates network error
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.NETWORK_ERROR)
        self.assertIsNotNone(result.error_message)
        
        # Verify JobFailedEvent published with correct category
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.error_category, ErrorCategory.NETWORK_ERROR.value)
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_handle_error_categorizes_validation_errors(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _handle_error categorizes validation errors correctly."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise validation error
        from yt_dlp.utils import ExtractorError
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = ExtractorError("Unsupported URL")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates invalid URL
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.INVALID_URL)
        self.assertIsNotNone(result.error_message)
        
        # Verify JobFailedEvent published with correct category
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.error_category, ErrorCategory.INVALID_URL.value)
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_handle_error_categorizes_format_errors(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _handle_error categorizes format errors correctly."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise format error
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("Requested format not available")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates format not supported
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.FORMAT_NOT_SUPPORTED)
        self.assertIsNotNone(result.error_message)
        
        # Verify JobFailedEvent published with correct category
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.error_category, ErrorCategory.FORMAT_NOT_SUPPORTED.value)
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_handle_error_categorizes_geo_blocked_errors(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _handle_error categorizes geo-blocked errors correctly."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise geo-blocked error
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("HTTP Error 403: Video not available in your region")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates geo-blocked
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.GEO_BLOCKED)
        self.assertIsNotNone(result.error_message)
        
        # Verify JobFailedEvent published with correct category
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.error_category, ErrorCategory.GEO_BLOCKED.value)
    
    @patch('application.download_service.YoutubeDL')
    @patch('application.download_service.Path')
    def test_handle_error_categorizes_rate_limit_errors(
        self,
        mock_path_class,
        mock_youtubedl_class
    ):
        """Test _handle_error categorizes rate limit errors correctly."""
        # Setup mocks
        job_manager, file_manager, video_processor, storage_service, event_publisher = create_mock_dependencies()
        
        # Mock YoutubeDL to raise rate limit error
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("HTTP Error 429: Too many requests")
        mock_youtubedl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        # Create service
        service = DownloadService(
            job_manager,
            file_manager,
            video_processor,
            storage_service,
            event_publisher
        )
        
        # Execute download
        result = service.execute_download(
            job_id="job-123",
            url="https://youtube.com/watch?v=test",
            format_id="137+140"
        )
        
        # Verify result indicates platform rate limited
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, ErrorCategory.PLATFORM_RATE_LIMITED)
        self.assertIsNotNone(result.error_message)
        
        # Verify JobFailedEvent published with correct category
        failed_event_call = event_publisher.publish.call_args_list[-1]
        failed_event = failed_event_call[0][0]
        self.assertIsInstance(failed_event, JobFailedEvent)
        self.assertEqual(failed_event.error_category, ErrorCategory.PLATFORM_RATE_LIMITED.value)


if __name__ == '__main__':
    unittest.main()
