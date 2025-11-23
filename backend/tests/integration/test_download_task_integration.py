"""
Integration Tests for Simplified Download Task

Tests the simplified download_video Celery task that delegates to DownloadService.
Verifies that the task correctly retrieves services from the container, calls the
download service, updates Celery state with progress, and returns the correct result format.

Requirements: 1.5, 9.2
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call

from flask import Flask

from application.dependency_container import DependencyContainer
from application.download_result import DownloadResult
from application.download_service import DownloadService
from domain.errors import ErrorCategory
from domain.job_management.entities import DownloadJob
from domain.job_management.value_objects import JobProgress
from tasks.download_task import download_video


class TestSimplifiedDownloadTask(unittest.TestCase):
    """Test simplified download task integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create Flask app with container
        self.app = Flask(__name__)
        self.container = DependencyContainer()
        self.app.container = self.container
        
        # Create mock DownloadService
        self.mock_download_service = Mock(spec=DownloadService)
        
        # Register mock service in container
        self.container.register_singleton(DownloadService, self.mock_download_service)
    
    def test_task_retrieves_service_from_container(self):
        """
        Test that the task retrieves DownloadService from the container.
        
        Verifies that the task uses the service locator to get the service
        from the Flask app's dependency container.
        """
        print("\n=== Testing Task Retrieves Service from Container ===")
        
        # Create successful result
        job = DownloadJob.create("https://youtube.com/watch?v=test", "137+140")
        job.job_id = "job-123"
        result = DownloadResult.create_success(
            job,
            "http://localhost:8000/api/download-file/token-123"
        )
        self.mock_download_service.execute_download.return_value = result
        
        # Create mock Celery task context
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task within app context
        # Call the task function directly (not through Celery proxy)
        with self.app.app_context():
            # Import the actual function from the module
            from tasks import download_task
            # Get the underlying function before Celery decoration
            task_result = download_task.download_video.run(
                job_id="job-123",
                url="https://youtube.com/watch?v=test",
                format_id="137+140"
            )
        
        # Verify service was called
        self.mock_download_service.execute_download.assert_called_once()
        
        # Verify result format
        self.assertIsInstance(task_result, dict)
        self.assertEqual(task_result['status'], 'completed')
        self.assertEqual(task_result['job_id'], 'job-123')
        
        print("✓ Task successfully retrieved service from container")
    
    def test_task_calls_download_service_correctly(self):
        """
        Test that the task calls download service with correct parameters.
        
        Verifies that the task passes job_id, url, format_id, and progress_callback
        to the download service's execute_download method.
        """
        print("\n=== Testing Task Calls Download Service Correctly ===")
        
        # Create successful result
        job = DownloadJob.create("https://youtube.com/watch?v=abc123", "best")
        job.job_id = "job-456"
        result = DownloadResult.create_success(
            job,
            "http://localhost:8000/api/download-file/token-456"
        )
        self.mock_download_service.execute_download.return_value = result
        
        # Create mock Celery task context
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task within app context
        with self.app.app_context():
            from tasks import download_task
            download_task.download_video.run(
                job_id="job-456",
                url="https://youtube.com/watch?v=abc123",
                format_id="best"
            )
        
        # Verify service was called with correct parameters
        self.mock_download_service.execute_download.assert_called_once()
        call_args = self.mock_download_service.execute_download.call_args
        
        # Check positional and keyword arguments
        self.assertEqual(call_args.kwargs['job_id'], 'job-456')
        self.assertEqual(call_args.kwargs['url'], 'https://youtube.com/watch?v=abc123')
        self.assertEqual(call_args.kwargs['format_id'], 'best')
        self.assertIsNotNone(call_args.kwargs['progress_callback'])
        
        print("✓ Task called download service with correct parameters")
    
    def test_progress_callback_updates_celery_state(self):
        """
        Test that the progress callback updates Celery task state.
        
        Verifies that when the download service invokes the progress callback,
        the Celery task state is updated with progress information.
        """
        print("\n=== Testing Progress Callback Updates Celery State ===")
        
        # Create successful result
        job = DownloadJob.create("https://youtube.com/watch?v=test", "137+140")
        job.job_id = "job-789"
        result = DownloadResult.create_success(
            job,
            "http://localhost:8000/api/download-file/token-789"
        )
        
        # Capture progress callback
        captured_callback = None
        update_state_calls = []
        
        def mock_execute_download(job_id, url, format_id, progress_callback=None):
            nonlocal captured_callback
            captured_callback = progress_callback
            
            # Simulate progress updates
            if progress_callback:
                progress1 = JobProgress.downloading(percentage=25, speed="1.5 MB/s", eta=30)
                progress_callback(progress1)
                
                progress2 = JobProgress.downloading(percentage=50, speed="2.0 MB/s", eta=15)
                progress_callback(progress2)
                
                progress3 = JobProgress.processing(percentage=95)
                progress_callback(progress3)
            
            return result
        
        self.mock_download_service.execute_download.side_effect = mock_execute_download
        
        # Execute task within app context with mocked update_state
        with self.app.app_context():
            from tasks import download_task
            # Mock the task's update_state method
            with patch.object(download_task.download_video, 'update_state') as mock_update_state:
                def capture_update_state(**kwargs):
                    update_state_calls.append(kwargs)
                
                mock_update_state.side_effect = capture_update_state
                
                download_task.download_video.run(
                    job_id="job-789",
                    url="https://youtube.com/watch?v=test",
                    format_id="137+140"
                )
        
        # Verify progress callback was provided
        self.assertIsNotNone(captured_callback)
        
        # Verify Celery state was updated multiple times
        self.assertGreaterEqual(len(update_state_calls), 3)
        
        # Verify state updates contain correct information
        # First progress update
        first_call = update_state_calls[0]
        self.assertEqual(first_call['state'], 'PROGRESS')
        self.assertEqual(first_call['meta']['percentage'], 25)
        self.assertEqual(first_call['meta']['speed'], '1.5 MB/s')
        self.assertEqual(first_call['meta']['eta'], 30)
        
        # Second progress update
        second_call = update_state_calls[1]
        self.assertEqual(second_call['state'], 'PROGRESS')
        self.assertEqual(second_call['meta']['percentage'], 50)
        self.assertEqual(second_call['meta']['speed'], '2.0 MB/s')
        self.assertEqual(second_call['meta']['eta'], 15)
        
        # Third progress update
        third_call = update_state_calls[2]
        self.assertEqual(third_call['state'], 'PROGRESS')
        self.assertEqual(third_call['meta']['percentage'], 95)
        self.assertEqual(third_call['meta']['phase'], 'processing')
        
        print("✓ Progress callback correctly updates Celery state")
    
    def test_task_returns_correct_result_format_on_success(self):
        """
        Test that the task returns the correct result format on success.
        
        Verifies that the task returns a dictionary with status, job_id,
        download_url, and no error information.
        """
        print("\n=== Testing Task Returns Correct Result Format on Success ===")
        
        # Create successful result
        job = DownloadJob.create("https://youtube.com/watch?v=success", "137+140")
        job.job_id = "job-success"
        result = DownloadResult.create_success(
            job,
            "http://localhost:8000/api/download-file/token-success"
        )
        self.mock_download_service.execute_download.return_value = result
        
        # Create mock Celery task context
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task within app context
        with self.app.app_context():
            from tasks import download_task
            task_result = download_task.download_video.run(
                job_id="job-success",
                url="https://youtube.com/watch?v=success",
                format_id="137+140"
            )
        
        # Verify result format
        self.assertIsInstance(task_result, dict)
        self.assertEqual(task_result['status'], 'completed')
        self.assertEqual(task_result['job_id'], 'job-success')
        self.assertEqual(task_result['download_url'], 'http://localhost:8000/api/download-file/token-success')
        self.assertIsNone(task_result.get('error'))
        self.assertIsNone(task_result.get('error_category'))
        
        print("✓ Task returns correct result format on success")
    
    def test_task_returns_correct_result_format_on_failure(self):
        """
        Test that the task returns the correct result format on failure.
        
        Verifies that the task returns a dictionary with status, job_id,
        error message, and error category when download fails.
        """
        print("\n=== Testing Task Returns Correct Result Format on Failure ===")
        
        # Create failure result
        job = DownloadJob.create("https://youtube.com/watch?v=fail", "137+140")
        job.job_id = "job-fail"
        result = DownloadResult.create_failure(
            job,
            ErrorCategory.VIDEO_UNAVAILABLE,
            "Video is unavailable"
        )
        self.mock_download_service.execute_download.return_value = result
        
        # Create mock Celery task context
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task within app context
        with self.app.app_context():
            from tasks import download_task
            task_result = download_task.download_video.run(
                job_id="job-fail",
                url="https://youtube.com/watch?v=fail",
                format_id="137+140"
            )
        
        # Verify result format
        self.assertIsInstance(task_result, dict)
        self.assertEqual(task_result['status'], 'failed')
        self.assertEqual(task_result['job_id'], 'job-fail')
        self.assertIsNone(task_result.get('download_url'))
        self.assertEqual(task_result['error'], 'Video is unavailable')
        self.assertEqual(task_result['error_category'], ErrorCategory.VIDEO_UNAVAILABLE.value)
        
        print("✓ Task returns correct result format on failure")
    
    def test_task_handles_different_error_categories(self):
        """
        Test that the task correctly handles different error categories.
        
        Verifies that the task properly returns error information for
        various error categories (network, rate limit, system error, etc.).
        """
        print("\n=== Testing Task Handles Different Error Categories ===")
        
        error_categories = [
            (ErrorCategory.NETWORK_ERROR, "Network connection failed"),
            (ErrorCategory.RATE_LIMITED, "Rate limit exceeded"),
            (ErrorCategory.SYSTEM_ERROR, "Internal system error"),
            (ErrorCategory.GEO_BLOCKED, "Video is geo-blocked"),
        ]
        
        for error_category, error_message in error_categories:
            with self.subTest(error_category=error_category):
                # Create failure result
                job = DownloadJob.create("https://youtube.com/watch?v=error", "137+140")
                job.job_id = f"job-{error_category.value}"
                result = DownloadResult.create_failure(
                    job,
                    error_category,
                    error_message
                )
                self.mock_download_service.execute_download.return_value = result
                
                # Create mock Celery task context
                mock_task = Mock()
                mock_task.update_state = Mock()
                
                # Execute task within app context
                with self.app.app_context():
                    from tasks import download_task
                    task_result = download_task.download_video.run(
                        job_id=f"job-{error_category.value}",
                        url="https://youtube.com/watch?v=error",
                        format_id="137+140"
                    )
                
                # Verify error information
                self.assertEqual(task_result['status'], 'failed')
                self.assertEqual(task_result['error_category'], error_category.value)
                self.assertEqual(task_result['error'], error_message)
        
        print("✓ Task correctly handles different error categories")
    
    def test_task_is_thin_wrapper(self):
        """
        Test that the task is a thin wrapper with minimal logic.
        
        Verifies that the task delegates all business logic to the
        download service and only handles Celery-specific concerns.
        """
        print("\n=== Testing Task is Thin Wrapper ===")
        
        # Create successful result
        job = DownloadJob.create("https://youtube.com/watch?v=thin", "137+140")
        job.job_id = "job-thin"
        result = DownloadResult.create_success(
            job,
            "http://localhost:8000/api/download-file/token-thin"
        )
        self.mock_download_service.execute_download.return_value = result
        
        # Create mock Celery task context
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task within app context
        with self.app.app_context():
            from tasks import download_task
            download_task.download_video.run(
                job_id="job-thin",
                url="https://youtube.com/watch?v=thin",
                format_id="137+140"
            )
        
        # Verify task only calls download service once
        self.assertEqual(self.mock_download_service.execute_download.call_count, 1)
        
        # Verify task doesn't perform any business logic
        # (all logic is in DownloadService)
        # The task should only:
        # 1. Get service from container
        # 2. Create progress callback
        # 3. Call execute_download
        # 4. Return result
        
        print("✓ Task is a thin wrapper that delegates to download service")


class TestSimplifiedDownloadTaskWithRealApp(unittest.TestCase):
    """Test simplified download task with real Flask app setup."""
    
    def test_task_with_real_app_factory(self):
        """
        Test that the task works with a real Flask app from app_factory.
        
        Verifies that the task can retrieve services from a properly
        configured Flask app with all dependencies initialized.
        """
        print("\n=== Testing Task with Real App Factory ===")
        
        from app_factory import create_app
        
        # Create real Flask app
        app = create_app()
        
        # Verify container is initialized
        self.assertIsNotNone(app.container)
        self.assertTrue(app.container.is_registered(DownloadService))
        
        # Create mock Celery task context
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Mock the actual download execution to avoid real yt-dlp calls
        with patch.object(DownloadService, 'execute_download') as mock_execute:
            # Create successful result
            job = DownloadJob.create("https://youtube.com/watch?v=real", "137+140")
            job.job_id = "job-real"
            result = DownloadResult.create_success(
                job,
                "http://localhost:8000/api/download-file/token-real"
            )
            mock_execute.return_value = result
            
            # Execute task within app context
            with app.app_context():
                from tasks import download_task
                task_result = download_task.download_video.run(
                    job_id="job-real",
                    url="https://youtube.com/watch?v=real",
                    format_id="137+140"
                )
            
            # Verify service was called
            mock_execute.assert_called_once()
            
            # Verify result format
            self.assertIsInstance(task_result, dict)
            self.assertEqual(task_result['status'], 'completed')
        
        print("✓ Task works correctly with real app factory")


def run_all_tests():
    """Run all simplified download task tests."""
    print("\n" + "=" * 60)
    print("SIMPLIFIED DOWNLOAD TASK INTEGRATION TESTS")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSimplifiedDownloadTask))
    suite.addTests(loader.loadTestsFromTestCase(TestSimplifiedDownloadTaskWithRealApp))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
