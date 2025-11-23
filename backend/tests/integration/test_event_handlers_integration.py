"""
Integration Tests for Event Handlers

Tests the WebSocketEventHandler infrastructure component for domain event handling.
Requirements: 9.2
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from domain.events import (
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent,
    JobStartedEvent,
)
from domain.job_management.value_objects import JobProgress
from infrastructure.event_handlers import WebSocketEventHandler


def test_handle_job_started_with_socketio_enabled():
    """
    Test that handle_job_started logs event when SocketIO is enabled.
    
    Verifies that the handler processes JobStartedEvent correctly
    when SocketIO is enabled.
    """
    print("\n=== Testing Handle Job Started with SocketIO Enabled ===")
    
    handler = WebSocketEventHandler()
    
    event = JobStartedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        url="https://youtube.com/watch?v=test",
        format_id="137+140"
    )
    
    # Mock SocketIO as enabled
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True):
        # Should not raise exception
        handler.handle_job_started(event)
    
    print("✓ JobStartedEvent handled successfully with SocketIO enabled")
    return True


def test_handle_job_started_with_socketio_disabled():
    """
    Test that handle_job_started works when SocketIO is disabled.
    
    Verifies that the handler gracefully handles the case where
    SocketIO is not available.
    """
    print("\n=== Testing Handle Job Started with SocketIO Disabled ===")
    
    handler = WebSocketEventHandler()
    
    event = JobStartedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        url="https://youtube.com/watch?v=test",
        format_id="137+140"
    )
    
    # Mock SocketIO as disabled
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=False):
        # Should not raise exception
        handler.handle_job_started(event)
    
    print("✓ JobStartedEvent handled successfully with SocketIO disabled")
    return True


def test_handle_job_progress_emits_websocket():
    """
    Test that handle_job_progress emits WebSocket message.
    
    Verifies that the handler calls emit_job_progress with correct data
    when SocketIO is enabled.
    """
    print("\n=== Testing Handle Job Progress Emits WebSocket ===")
    
    handler = WebSocketEventHandler()
    
    progress = JobProgress(percentage=50, phase="Downloading")
    event = JobProgressUpdatedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        progress=progress
    )
    
    # Mock SocketIO and emit function
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True), \
         patch('infrastructure.event_handlers.emit_job_progress') as mock_emit:
        
        handler.handle_job_progress(event)
        
        # Verify emit was called with correct arguments
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        
        assert call_args[0][0] == "job-123", "Job ID should match"
        assert call_args[0][1] == progress.to_dict(), "Progress data should match"
    
    print("✓ JobProgressUpdatedEvent emitted WebSocket message correctly")
    return True


def test_handle_job_progress_with_socketio_disabled():
    """
    Test that handle_job_progress works when SocketIO is disabled.
    
    Verifies that the handler doesn't attempt to emit when SocketIO
    is not available.
    """
    print("\n=== Testing Handle Job Progress with SocketIO Disabled ===")
    
    handler = WebSocketEventHandler()
    
    progress = JobProgress(percentage=75, phase="Processing")
    event = JobProgressUpdatedEvent(
        aggregate_id="job-456",
        occurred_at=datetime.utcnow(),
        progress=progress
    )
    
    # Mock SocketIO as disabled
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=False), \
         patch('infrastructure.event_handlers.emit_job_progress') as mock_emit:
        
        handler.handle_job_progress(event)
        
        # Verify emit was NOT called
        mock_emit.assert_not_called()
    
    print("✓ JobProgressUpdatedEvent handled without emission when SocketIO disabled")
    return True


def test_handle_job_completed_emits_websocket():
    """
    Test that handle_job_completed emits WebSocket message.
    
    Verifies that the handler calls emit_job_completed with correct data
    when SocketIO is enabled.
    """
    print("\n=== Testing Handle Job Completed Emits WebSocket ===")
    
    handler = WebSocketEventHandler()
    
    download_url = "https://example.com/download/file.mp4"
    expire_at = datetime.utcnow() + timedelta(minutes=10)
    
    event = JobCompletedEvent(
        aggregate_id="job-789",
        occurred_at=datetime.utcnow(),
        download_url=download_url,
        expire_at=expire_at
    )
    
    # Mock SocketIO and emit function
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True), \
         patch('infrastructure.event_handlers.emit_job_completed') as mock_emit:
        
        handler.handle_job_completed(event)
        
        # Verify emit was called with correct arguments
        mock_emit.assert_called_once_with(
            "job-789",
            download_url,
            expire_at
        )
    
    print("✓ JobCompletedEvent emitted WebSocket message correctly")
    return True


def test_handle_job_completed_with_socketio_disabled():
    """
    Test that handle_job_completed works when SocketIO is disabled.
    
    Verifies that the handler doesn't attempt to emit when SocketIO
    is not available.
    """
    print("\n=== Testing Handle Job Completed with SocketIO Disabled ===")
    
    handler = WebSocketEventHandler()
    
    event = JobCompletedEvent(
        aggregate_id="job-999",
        occurred_at=datetime.utcnow(),
        download_url="https://example.com/file.mp4",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    # Mock SocketIO as disabled
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=False), \
         patch('infrastructure.event_handlers.emit_job_completed') as mock_emit:
        
        handler.handle_job_completed(event)
        
        # Verify emit was NOT called
        mock_emit.assert_not_called()
    
    print("✓ JobCompletedEvent handled without emission when SocketIO disabled")
    return True


def test_handle_job_failed_emits_websocket():
    """
    Test that handle_job_failed emits WebSocket message.
    
    Verifies that the handler calls emit_job_failed with correct data
    when SocketIO is enabled.
    """
    print("\n=== Testing Handle Job Failed Emits WebSocket ===")
    
    handler = WebSocketEventHandler()
    
    error_message = "Video unavailable"
    error_category = "VIDEO_UNAVAILABLE"
    
    event = JobFailedEvent(
        aggregate_id="job-error-123",
        occurred_at=datetime.utcnow(),
        error_message=error_message,
        error_category=error_category
    )
    
    # Mock SocketIO and emit function
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True), \
         patch('infrastructure.event_handlers.emit_job_failed') as mock_emit:
        
        handler.handle_job_failed(event)
        
        # Verify emit was called with correct arguments
        mock_emit.assert_called_once_with(
            "job-error-123",
            error_message,
            error_category
        )
    
    print("✓ JobFailedEvent emitted WebSocket message correctly")
    return True


def test_handle_job_failed_with_socketio_disabled():
    """
    Test that handle_job_failed works when SocketIO is disabled.
    
    Verifies that the handler doesn't attempt to emit when SocketIO
    is not available.
    """
    print("\n=== Testing Handle Job Failed with SocketIO Disabled ===")
    
    handler = WebSocketEventHandler()
    
    event = JobFailedEvent(
        aggregate_id="job-error-456",
        occurred_at=datetime.utcnow(),
        error_message="Download failed",
        error_category="DOWNLOAD_ERROR"
    )
    
    # Mock SocketIO as disabled
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=False), \
         patch('infrastructure.event_handlers.emit_job_failed') as mock_emit:
        
        handler.handle_job_failed(event)
        
        # Verify emit was NOT called
        mock_emit.assert_not_called()
    
    print("✓ JobFailedEvent handled without emission when SocketIO disabled")
    return True


def test_handler_exception_handling():
    """
    Test that handlers gracefully handle exceptions.
    
    Verifies that exceptions in emit functions don't crash the handler.
    """
    print("\n=== Testing Handler Exception Handling ===")
    
    handler = WebSocketEventHandler()
    
    event = JobCompletedEvent(
        aggregate_id="job-exception",
        occurred_at=datetime.utcnow(),
        download_url="https://example.com/file.mp4",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    # Mock emit to raise exception
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True), \
         patch('infrastructure.event_handlers.emit_job_completed', side_effect=Exception("Emit failed")):
        
        # Should not raise exception
        handler.handle_job_completed(event)
    
    print("✓ Handler handled exception gracefully")
    return True


def test_event_data_passed_correctly_to_emit():
    """
    Test that event data is correctly passed to emit functions.
    
    Verifies that all event attributes are properly extracted and
    passed to the WebSocket emit functions.
    """
    print("\n=== Testing Event Data Passed Correctly to Emit ===")
    
    handler = WebSocketEventHandler()
    
    # Test with JobProgressUpdatedEvent
    progress = JobProgress(
        percentage=85,
        phase="Finalizing",
        speed="512 KB/s",
        eta=15
    )
    
    event = JobProgressUpdatedEvent(
        aggregate_id="job-data-test",
        occurred_at=datetime.utcnow(),
        progress=progress
    )
    
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True), \
         patch('infrastructure.event_handlers.emit_job_progress') as mock_emit:
        
        handler.handle_job_progress(event)
        
        # Verify all progress data is passed
        call_args = mock_emit.call_args
        progress_dict = call_args[0][1]
        
        assert progress_dict['percentage'] == 85, "Percentage should match"
        assert progress_dict['phase'] == "Finalizing", "Phase should match"
        assert progress_dict['speed'] == "512 KB/s", "Speed should match"
        assert progress_dict['eta'] == 15, "ETA should match"
    
    print("✓ Event data passed correctly to emit function")
    return True


def test_multiple_event_types_handled():
    """
    Test that handler can process multiple event types in sequence.
    
    Verifies that the handler maintains state correctly across
    different event types.
    """
    print("\n=== Testing Multiple Event Types Handled ===")
    
    handler = WebSocketEventHandler()
    
    # Create events of different types
    started_event = JobStartedEvent(
        aggregate_id="job-multi",
        occurred_at=datetime.utcnow(),
        url="https://youtube.com/watch?v=test",
        format_id="137+140"
    )
    
    progress_event = JobProgressUpdatedEvent(
        aggregate_id="job-multi",
        occurred_at=datetime.utcnow(),
        progress=JobProgress(percentage=50, phase="Downloading")
    )
    
    completed_event = JobCompletedEvent(
        aggregate_id="job-multi",
        occurred_at=datetime.utcnow(),
        download_url="https://example.com/file.mp4",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    # Mock SocketIO and emit functions
    with patch('infrastructure.event_handlers.is_socketio_enabled', return_value=True), \
         patch('infrastructure.event_handlers.emit_job_progress') as mock_progress, \
         patch('infrastructure.event_handlers.emit_job_completed') as mock_completed:
        
        # Handle events in sequence
        handler.handle_job_started(started_event)
        handler.handle_job_progress(progress_event)
        handler.handle_job_completed(completed_event)
        
        # Verify correct emit functions were called
        mock_progress.assert_called_once()
        mock_completed.assert_called_once()
    
    print("✓ Multiple event types handled correctly in sequence")
    return True


def run_all_tests():
    """Run all event handler integration tests."""
    print("\n" + "=" * 60)
    print("EVENT HANDLER INTEGRATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Handle Job Started - SocketIO Enabled", test_handle_job_started_with_socketio_enabled),
        ("Handle Job Started - SocketIO Disabled", test_handle_job_started_with_socketio_disabled),
        ("Handle Job Progress - Emits WebSocket", test_handle_job_progress_emits_websocket),
        ("Handle Job Progress - SocketIO Disabled", test_handle_job_progress_with_socketio_disabled),
        ("Handle Job Completed - Emits WebSocket", test_handle_job_completed_emits_websocket),
        ("Handle Job Completed - SocketIO Disabled", test_handle_job_completed_with_socketio_disabled),
        ("Handle Job Failed - Emits WebSocket", test_handle_job_failed_emits_websocket),
        ("Handle Job Failed - SocketIO Disabled", test_handle_job_failed_with_socketio_disabled),
        ("Handler Exception Handling", test_handler_exception_handling),
        ("Event Data Passed Correctly to Emit", test_event_data_passed_correctly_to_emit),
        ("Multiple Event Types Handled", test_multiple_event_types_handled),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

