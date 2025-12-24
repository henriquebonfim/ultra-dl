"""
Unit tests for WebSocket events.

Tests WebSocket event emission, event routing, and room management.

Requirements: 12.1, 12.2, 12.4
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.api.websocket_events import (
    emit_job_progress,
    emit_job_completed,
    emit_job_failed,
    emit_job_cancelled,
)


@pytest.fixture
def mock_socketio():
    """Mock Flask-SocketIO instance."""
    socketio = Mock()
    socketio.emit = Mock()
    return socketio


# =============================================================================
# Test Progress Event Emission
# =============================================================================

def test_emit_job_progress_sends_correct_event(mock_socketio):
    """
    Test that progress events are emitted with correct structure.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        progress_data = {
            "percentage": 50,
            "phase": "downloading",
            "speed": "1.5 MB/s",
            "eta": "30s"
        }
        
        emit_job_progress("test-job-123", progress_data)
        
        # Verify emit was called
        mock_socketio.emit.assert_called_once()
        
        # Verify event name
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "job_progress"
        
        # Verify event data
        event_data = call_args[0][1]
        assert event_data["job_id"] == "test-job-123"
        assert event_data["progress"] == progress_data
        
        # Verify room routing
        assert call_args[1]["room"] == "test-job-123"


def test_emit_job_progress_with_different_phases(mock_socketio):
    """
    Test progress events for different processing phases.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        phases = ["metadata_extraction", "downloading", "processing", "finalizing"]
        
        for phase in phases:
            mock_socketio.reset_mock()
            progress_data = {
                "percentage": 25,
                "phase": phase,
                "speed": None,
                "eta": None
            }
            
            emit_job_progress("test-job-123", progress_data)
            
            call_args = mock_socketio.emit.call_args
            event_data = call_args[0][1]
            assert event_data["progress"]["phase"] == phase


def test_emit_job_progress_handles_socketio_unavailable():
    """
    Test that progress emission handles SocketIO being unavailable.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=None):
        # Should not raise exception
        emit_job_progress("test-job-123", {"percentage": 50})


# =============================================================================
# Test Completion Event Emission
# =============================================================================

def test_emit_job_completed_sends_correct_event(mock_socketio):
    """
    Test that completion events are emitted with correct structure.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        download_url = "https://example.com/download/test-token"
        expire_at = datetime.utcnow() + timedelta(minutes=10)
        
        emit_job_completed("test-job-123", download_url, expire_at)
        
        # Verify emit was called
        mock_socketio.emit.assert_called_once()
        
        # Verify event name
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "job_completed"
        
        # Verify event data
        event_data = call_args[0][1]
        assert event_data["job_id"] == "test-job-123"
        assert event_data["status"] == "completed"
        assert event_data["download_url"] == download_url
        assert "expire_at" in event_data
        
        # Verify room routing
        assert call_args[1]["room"] == "test-job-123"


def test_emit_job_completed_without_expiration(mock_socketio):
    """
    Test completion event without expiration time.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        download_url = "https://example.com/download/test-token"
        
        emit_job_completed("test-job-123", download_url, expire_at=None)
        
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]
        assert event_data["job_id"] == "test-job-123"
        assert event_data["download_url"] == download_url
        # expire_at should not be in event data when None
        assert "expire_at" not in event_data or event_data.get("expire_at") is None


# =============================================================================
# Test Error Event Emission
# =============================================================================

def test_emit_job_failed_sends_correct_event(mock_socketio):
    """
    Test that error events are emitted with correct structure.
    
    Validates: Requirements 12.2
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        error_message = "Video unavailable"
        error_category = "video_unavailable"
        
        emit_job_failed("test-job-123", error_message, error_category)
        
        # Verify emit was called
        mock_socketio.emit.assert_called_once()
        
        # Verify event name
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "job_failed"
        
        # Verify event data
        event_data = call_args[0][1]
        assert event_data["job_id"] == "test-job-123"
        assert event_data["status"] == "failed"
        assert event_data["error"] == error_message
        assert event_data["error_category"] == error_category
        
        # Verify room routing
        assert call_args[1]["room"] == "test-job-123"


def test_emit_job_failed_without_category(mock_socketio):
    """
    Test error event without error category.
    
    Validates: Requirements 12.2
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        error_message = "Unknown error"
        
        emit_job_failed("test-job-123", error_message, error_category=None)
        
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]
        assert event_data["error"] == error_message
        # error_category should not be in event data when None
        assert "error_category" not in event_data or event_data.get("error_category") is None


def test_emit_job_failed_with_different_error_categories(mock_socketio):
    """
    Test error events with different error categories.
    
    Validates: Requirements 12.2
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        error_categories = [
            "invalid_url",
            "video_unavailable",
            "download_failed",
            "rate_limited",
            "system_error"
        ]
        
        for category in error_categories:
            mock_socketio.reset_mock()
            emit_job_failed("test-job-123", f"Error: {category}", category)
            
            call_args = mock_socketio.emit.call_args
            event_data = call_args[0][1]
            assert event_data["error_category"] == category


# =============================================================================
# Test Cancellation Event Emission
# =============================================================================

def test_emit_job_cancelled_sends_correct_event(mock_socketio):
    """
    Test that cancellation events are emitted correctly.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        emit_job_cancelled("test-job-123")
        
        # Verify emit was called
        mock_socketio.emit.assert_called_once()
        
        # Verify event name
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "job_cancelled"
        
        # Verify event data
        event_data = call_args[0][1]
        assert event_data["job_id"] == "test-job-123"
        assert event_data["status"] == "cancelled"
        
        # Verify room routing
        assert call_args[1]["room"] == "test-job-123"


# =============================================================================
# Test Event Routing to Correct Rooms
# =============================================================================

def test_events_routed_to_correct_job_room(mock_socketio):
    """
    Test that events are routed to the correct job-specific room.
    
    Validates: Requirements 12.4
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        job_ids = ["job-1", "job-2", "job-3"]
        
        for job_id in job_ids:
            mock_socketio.reset_mock()
            emit_job_progress(job_id, {"percentage": 50})
            
            call_args = mock_socketio.emit.call_args
            assert call_args[1]["room"] == job_id


def test_multiple_events_for_same_job_use_same_room(mock_socketio):
    """
    Test that multiple events for the same job use the same room.
    
    Validates: Requirements 12.4
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        job_id = "test-job-123"
        
        # Emit different events for same job
        emit_job_progress(job_id, {"percentage": 25})
        call_1 = mock_socketio.emit.call_args
        
        emit_job_progress(job_id, {"percentage": 50})
        call_2 = mock_socketio.emit.call_args
        
        emit_job_completed(job_id, "https://example.com/download")
        call_3 = mock_socketio.emit.call_args
        
        # All should use the same room
        assert call_1[1]["room"] == job_id
        assert call_2[1]["room"] == job_id
        assert call_3[1]["room"] == job_id


# =============================================================================
# Test Error Handling
# =============================================================================

def test_emit_handles_socketio_emit_failure(mock_socketio):
    """
    Test that emit functions handle SocketIO emit failures gracefully.
    
    Validates: Requirements 12.1, 12.2
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        mock_socketio.emit.side_effect = Exception("SocketIO error")
        
        # Should not raise exception
        emit_job_progress("test-job-123", {"percentage": 50})
        emit_job_completed("test-job-123", "https://example.com/download")
        emit_job_failed("test-job-123", "Error message")
        emit_job_cancelled("test-job-123")


# =============================================================================
# Test Event Data Structure
# =============================================================================

def test_progress_event_has_required_fields(mock_socketio):
    """
    Test that progress events have all required fields.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        progress_data = {
            "percentage": 75,
            "phase": "downloading",
            "speed": "2.0 MB/s",
            "eta": "15s"
        }
        
        emit_job_progress("test-job-123", progress_data)
        
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]
        
        # Check required fields
        assert "job_id" in event_data
        assert "progress" in event_data
        assert "percentage" in event_data["progress"]
        assert "phase" in event_data["progress"]


def test_completed_event_has_required_fields(mock_socketio):
    """
    Test that completion events have all required fields.
    
    Validates: Requirements 12.1
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        emit_job_completed("test-job-123", "https://example.com/download")
        
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]
        
        # Check required fields
        assert "job_id" in event_data
        assert "status" in event_data
        assert "download_url" in event_data
        assert event_data["status"] == "completed"


def test_failed_event_has_required_fields(mock_socketio):
    """
    Test that error events have all required fields.
    
    Validates: Requirements 12.2
    """
    with patch('src.api.websocket_events.get_socketio', return_value=mock_socketio):
        emit_job_failed("test-job-123", "Error message", "error_category")
        
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]
        
        # Check required fields
        assert "job_id" in event_data
        assert "status" in event_data
        assert "error" in event_data
        assert event_data["status"] == "failed"
