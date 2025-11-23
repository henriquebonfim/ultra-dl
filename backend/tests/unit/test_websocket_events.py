"""
Unit Tests for WebSocket Events

Tests WebSocket event handlers and emitters for real-time progress updates.
Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestWebSocketEmitters(unittest.TestCase):
    """Unit tests for event emission functions."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.mock_socketio = Mock()

    def test_emit_job_progress_broadcasts_to_correct_room(self):
        """Test emit_job_progress broadcasts to correct room.

        Requirements: 2.2, 2.3
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_progress

            progress_data = {
                "percentage": 50,
                "phase": "downloading",
                "speed": "2 MB/s",
                "eta": 30,
            }

            emit_job_progress("job-123", progress_data)

            # Verify socketio.emit was called
            self.mock_socketio.emit.assert_called_once()
            call_args = self.mock_socketio.emit.call_args

            # Verify event name
            self.assertEqual(call_args[0][0], "job_progress")

            # Verify room
            self.assertEqual(call_args[1]["room"], "job-123")

            # Verify job_id in data
            self.assertEqual(call_args[0][1]["job_id"], "job-123")

    def test_emit_job_progress_includes_all_progress_data_fields(self):
        """Test emit_job_progress includes all progress data fields.

        Requirements: 2.2, 2.5
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_progress

            progress_data = {
                "percentage": 75,
                "phase": "processing",
                "speed": "5 MB/s",
                "eta": 15,
                "downloaded_bytes": 7500000,
                "total_bytes": 10000000,
            }

            emit_job_progress("job-456", progress_data)

            # Verify all fields are included
            call_args = self.mock_socketio.emit.call_args
            emitted_progress = call_args[0][1]["progress"]

            self.assertEqual(emitted_progress["percentage"], 75)
            self.assertEqual(emitted_progress["phase"], "processing")
            self.assertEqual(emitted_progress["speed"], "5 MB/s")
            self.assertEqual(emitted_progress["eta"], 15)
            self.assertEqual(emitted_progress["downloaded_bytes"], 7500000)
            self.assertEqual(emitted_progress["total_bytes"], 10000000)

    def test_emit_job_completed_includes_download_url(self):
        """Test emit_job_completed includes download_url.

        Requirements: 2.2, 2.3
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_completed

            download_url = "http://example.com/download/token123"

            emit_job_completed("job-789", download_url)

            # Verify download_url is included
            call_args = self.mock_socketio.emit.call_args
            event_data = call_args[0][1]

            self.assertEqual(event_data["job_id"], "job-789")
            self.assertEqual(event_data["status"], "completed")
            self.assertEqual(event_data["download_url"], download_url)

    def test_emit_job_completed_includes_expire_at_when_provided(self):
        """Test emit_job_completed includes expire_at when provided.

        Requirements: 2.2, 2.5
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_completed

            download_url = "http://example.com/download/token456"
            expire_at = datetime.utcnow() + timedelta(minutes=15)

            emit_job_completed("job-101", download_url, expire_at)

            # Verify expire_at is included
            call_args = self.mock_socketio.emit.call_args
            event_data = call_args[0][1]

            self.assertIn("expire_at", event_data)
            self.assertEqual(event_data["expire_at"], expire_at.isoformat())

    def test_emit_job_completed_omits_expire_at_when_none(self):
        """Test emit_job_completed omits expire_at when None.

        Requirements: 2.2, 2.5
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_completed

            download_url = "http://example.com/download/token789"

            emit_job_completed("job-202", download_url, expire_at=None)

            # Verify expire_at is not included
            call_args = self.mock_socketio.emit.call_args
            event_data = call_args[0][1]

            self.assertNotIn("expire_at", event_data)

    def test_emit_job_failed_includes_error_message(self):
        """Test emit_job_failed includes error_message.

        Requirements: 2.2, 2.4
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_failed

            error_message = "Video unavailable"

            emit_job_failed("job-303", error_message)

            # Verify error_message is included
            call_args = self.mock_socketio.emit.call_args
            event_data = call_args[0][1]

            self.assertEqual(event_data["job_id"], "job-303")
            self.assertEqual(event_data["status"], "failed")
            self.assertEqual(event_data["error"], error_message)

    def test_emit_job_failed_includes_error_category_when_provided(self):
        """Test emit_job_failed includes error_category when provided.

        Requirements: 2.2, 2.5
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_failed

            error_message = "Network timeout"
            error_category = "NETWORK_ERROR"

            emit_job_failed("job-404", error_message, error_category)

            # Verify error_category is included
            call_args = self.mock_socketio.emit.call_args
            event_data = call_args[0][1]

            self.assertIn("error_category", event_data)
            self.assertEqual(event_data["error_category"], error_category)

    def test_emit_job_cancelled_broadcasts_to_correct_room(self):
        """Test emit_job_cancelled broadcasts to correct room.

        Requirements: 2.2, 2.3
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            from api.websocket_events import emit_job_cancelled

            emit_job_cancelled("job-505")

            # Verify socketio.emit was called
            self.mock_socketio.emit.assert_called_once()
            call_args = self.mock_socketio.emit.call_args

            # Verify event name
            self.assertEqual(call_args[0][0], "job_cancelled")

            # Verify room
            self.assertEqual(call_args[1]["room"], "job-505")

            # Verify job_id and status in data
            event_data = call_args[0][1]
            self.assertEqual(event_data["job_id"], "job-505")
            self.assertEqual(event_data["status"], "cancelled")

    def test_emit_functions_handle_socketio_none_gracefully(self):
        """Test all emit functions handle socketio=None gracefully.

        Requirements: 2.5
        """
        with patch("api.websocket_events.get_socketio", return_value=None):
            from api.websocket_events import (
                emit_job_cancelled,
                emit_job_completed,
                emit_job_failed,
                emit_job_progress,
            )

            # All these should not raise exceptions
            try:
                emit_job_progress("job-606", {"percentage": 50})
                emit_job_completed("job-606", "http://example.com/download")
                emit_job_failed("job-606", "Error message")
                emit_job_cancelled("job-606")
            except Exception as e:
                self.fail(
                    f"Emit functions should handle socketio=None gracefully, but raised: {e}"
                )

    def test_emit_functions_handle_exceptions_without_crashing(self):
        """Test all emit functions handle exceptions without crashing.

        Requirements: 2.5
        """
        mock_socketio = Mock()
        mock_socketio.emit.side_effect = Exception("SocketIO error")

        with patch("api.websocket_events.get_socketio", return_value=mock_socketio):
            from api.websocket_events import (
                emit_job_cancelled,
                emit_job_completed,
                emit_job_failed,
                emit_job_progress,
            )

            # All these should not raise exceptions
            try:
                emit_job_progress("job-707", {"percentage": 50})
                emit_job_completed("job-707", "http://example.com/download")
                emit_job_failed("job-707", "Error message")
                emit_job_cancelled("job-707")
            except Exception as e:
                self.fail(
                    f"Emit functions should handle exceptions gracefully, but raised: {e}"
                )


class TestWebSocketEventHandlers(unittest.TestCase):
    """Unit tests for WebSocket event handlers with mocked SocketIO."""

    def setUp(self):
        """Set up test fixtures before each test."""
        from flask import Flask

        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.mock_socketio = Mock()
        self.mock_job_service = Mock()

    def test_handle_connect_emits_connected_event_with_client_id(self):
        """Test handle_connect emits connected event with client_id.

        Requirements: 2.2
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                with patch("api.websocket_events.request") as mock_request:
                    mock_request.sid = "test-client-123"

                    # Import and register events
                    from api.websocket_events import register_socketio_events

                    register_socketio_events(self.app)

                    # Get the registered connect handler
                    connect_handler = None
                    for call_args in self.mock_socketio.on.call_args_list:
                        if len(call_args[0]) > 0 and call_args[0][0] == "connect":
                            connect_handler = (
                                call_args[0][1] if len(call_args[0]) > 1 else None
                            )
                            break

                    self.assertIsNotNone(
                        connect_handler, "Connect handler should be registered"
                    )

                    # Call the handler
                    connect_handler()

                    # Verify emit was called with correct data
                    mock_emit.assert_called_once()
                    call_args = mock_emit.call_args
                    self.assertEqual(call_args[0][0], "connected")
                    self.assertEqual(call_args[0][1]["client_id"], "test-client-123")
                    self.assertIn("message", call_args[0][1])

    def test_handle_disconnect_logs_client_disconnection(self):
        """Test handle_disconnect logs client disconnection.

        Requirements: 2.2
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.logger") as mock_logger:
                with patch("api.websocket_events.request") as mock_request:
                    mock_request.sid = "test-client-456"

                    # Import and register events
                    from api.websocket_events import register_socketio_events

                    register_socketio_events(self.app)

                    # Get the registered disconnect handler
                    disconnect_handler = None
                    for call_args in self.mock_socketio.on.call_args_list:
                        if len(call_args[0]) > 0 and call_args[0][0] == "disconnect":
                            disconnect_handler = (
                                call_args[0][1] if len(call_args[0]) > 1 else None
                            )
                            break

                    self.assertIsNotNone(
                        disconnect_handler, "Disconnect handler should be registered"
                    )

                    # Call the handler
                    disconnect_handler()

                    # Verify logging was called
                    mock_logger.info.assert_called()
                    log_message = str(mock_logger.info.call_args[0][0])
                    self.assertIn("test-client-456", log_message)
                    self.assertIn("disconnected", log_message.lower())

    def test_subscribe_job_joins_room_and_emits_subscribed_event(self):
        """Test subscribe_job joins room and emits subscribed event.

        Requirements: 2.3
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.join_room") as mock_join_room:
                with patch("api.websocket_events.emit") as mock_emit:
                    with patch("api.websocket_events.request") as mock_request:
                        mock_request.sid = "test-client-789"

                        # Import and register events
                        from api.websocket_events import register_socketio_events

                        register_socketio_events(self.app)

                        # Get the registered subscribe_job handler
                        subscribe_handler = None
                        for call_args in self.mock_socketio.on.call_args_list:
                            if (
                                len(call_args[0]) > 0
                                and call_args[0][0] == "subscribe_job"
                            ):
                                subscribe_handler = (
                                    call_args[0][1] if len(call_args[0]) > 1 else None
                                )
                                break

                        self.assertIsNotNone(
                            subscribe_handler, "Subscribe handler should be registered"
                        )

                        # Call the handler with job_id
                        subscribe_handler({"job_id": "job-123"})

                        # Verify join_room was called
                        mock_join_room.assert_called_once_with("job-123")

                        # Verify emit was called with subscribed event
                        mock_emit.assert_called_once()
                        call_args = mock_emit.call_args
                        self.assertEqual(call_args[0][0], "subscribed")
                        self.assertEqual(call_args[0][1]["job_id"], "job-123")

    def test_subscribe_job_with_missing_job_id_emits_error(self):
        """Test subscribe_job with missing job_id emits error.

        Requirements: 2.4
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                # Import and register events
                from api.websocket_events import register_socketio_events

                register_socketio_events(self.app)

                # Get the registered subscribe_job handler
                subscribe_handler = None
                for call_args in self.mock_socketio.on.call_args_list:
                    if len(call_args[0]) > 0 and call_args[0][0] == "subscribe_job":
                        subscribe_handler = (
                            call_args[0][1] if len(call_args[0]) > 1 else None
                        )
                        break

                self.assertIsNotNone(
                    subscribe_handler, "Subscribe handler should be registered"
                )

                # Call the handler without job_id
                subscribe_handler({})

                # Verify error was emitted
                mock_emit.assert_called_once()
                call_args = mock_emit.call_args
                self.assertEqual(call_args[0][0], "error")
                self.assertIn("Missing job_id", call_args[0][1]["message"])

    def test_unsubscribe_job_leaves_room_and_emits_unsubscribed_event(self):
        """Test unsubscribe_job leaves room and emits unsubscribed event.

        Requirements: 2.3
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.leave_room") as mock_leave_room:
                with patch("api.websocket_events.emit") as mock_emit:
                    with patch("api.websocket_events.request") as mock_request:
                        mock_request.sid = "test-client-101"

                        # Import and register events
                        from api.websocket_events import register_socketio_events

                        register_socketio_events(self.app)

                        # Get the registered unsubscribe_job handler
                        unsubscribe_handler = None
                        for call_args in self.mock_socketio.on.call_args_list:
                            if (
                                len(call_args[0]) > 0
                                and call_args[0][0] == "unsubscribe_job"
                            ):
                                unsubscribe_handler = (
                                    call_args[0][1] if len(call_args[0]) > 1 else None
                                )
                                break

                        self.assertIsNotNone(
                            unsubscribe_handler,
                            "Unsubscribe handler should be registered",
                        )

                        # Call the handler with job_id
                        unsubscribe_handler({"job_id": "job-456"})

                        # Verify leave_room was called
                        mock_leave_room.assert_called_once_with("job-456")

                        # Verify emit was called with unsubscribed event
                        mock_emit.assert_called_once()
                        call_args = mock_emit.call_args
                        self.assertEqual(call_args[0][0], "unsubscribed")
                        self.assertEqual(call_args[0][1]["job_id"], "job-456")

    def test_unsubscribe_job_with_missing_job_id_emits_error(self):
        """Test unsubscribe_job with missing job_id emits error.

        Requirements: 2.4
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                # Import and register events
                from api.websocket_events import register_socketio_events

                register_socketio_events(self.app)

                # Get the registered unsubscribe_job handler
                unsubscribe_handler = None
                for call_args in self.mock_socketio.on.call_args_list:
                    if len(call_args[0]) > 0 and call_args[0][0] == "unsubscribe_job":
                        unsubscribe_handler = (
                            call_args[0][1] if len(call_args[0]) > 1 else None
                        )
                        break

                self.assertIsNotNone(
                    unsubscribe_handler, "Unsubscribe handler should be registered"
                )

                # Call the handler without job_id
                unsubscribe_handler({})

                # Verify error was emitted
                mock_emit.assert_called_once()
                call_args = mock_emit.call_args
                self.assertEqual(call_args[0][0], "error")
                self.assertIn("Missing job_id", call_args[0][1]["message"])

    def test_ping_responds_with_pong_event(self):
        """Test ping responds with pong event.

        Requirements: 2.2
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                with patch("api.websocket_events.request") as mock_request:
                    mock_request.args = Mock()
                    mock_request.args.get.return_value = "1234567890"

                    # Import and register events
                    from api.websocket_events import register_socketio_events

                    register_socketio_events(self.app)

                    # Get the registered ping handler
                    ping_handler = None
                    for call_args in self.mock_socketio.on.call_args_list:
                        if len(call_args[0]) > 0 and call_args[0][0] == "ping":
                            ping_handler = (
                                call_args[0][1] if len(call_args[0]) > 1 else None
                            )
                            break

                    self.assertIsNotNone(
                        ping_handler, "Ping handler should be registered"
                    )

                    # Call the handler
                    ping_handler()

                    # Verify pong was emitted
                    mock_emit.assert_called_once()
                    call_args = mock_emit.call_args
                    self.assertEqual(call_args[0][0], "pong")
                    self.assertEqual(call_args[0][1]["timestamp"], "1234567890")

    def test_cancel_job_deletes_job_and_broadcasts_cancellation(self):
        """Test cancel_job deletes job and broadcasts cancellation.

        Requirements: 2.3, 2.4
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                with patch("api.websocket_events.request") as mock_request:
                    with patch("api.websocket_events.current_app") as mock_current_app:
                        mock_request.sid = "test-client-202"
                        self.mock_job_service.delete_job.return_value = True
                        mock_current_app.job_service = self.mock_job_service

                        # Import and register events
                        from api.websocket_events import register_socketio_events

                        register_socketio_events(self.app)

                        # Get the registered cancel_job handler
                        cancel_handler = None
                        for call_args in self.mock_socketio.on.call_args_list:
                            if (
                                len(call_args[0]) > 0
                                and call_args[0][0] == "cancel_job"
                            ):
                                cancel_handler = (
                                    call_args[0][1] if len(call_args[0]) > 1 else None
                                )
                                break

                        self.assertIsNotNone(
                            cancel_handler, "Cancel handler should be registered"
                        )

                        # Call the handler with job_id
                        cancel_handler({"job_id": "job-789"})

                        # Verify job_service.delete_job was called
                        self.mock_job_service.delete_job.assert_called_once_with(
                            "job-789"
                        )

                        # Verify emit was called for client response
                        self.assertTrue(mock_emit.called)

                        # Verify socketio.emit was called for broadcast
                        self.assertTrue(self.mock_socketio.emit.called)

    def test_cancel_job_with_missing_job_id_emits_error(self):
        """Test cancel_job with missing job_id emits error.

        Requirements: 2.4
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                # Import and register events
                from api.websocket_events import register_socketio_events

                register_socketio_events(self.app)

                # Get the registered cancel_job handler
                cancel_handler = None
                for call_args in self.mock_socketio.on.call_args_list:
                    if len(call_args[0]) > 0 and call_args[0][0] == "cancel_job":
                        cancel_handler = (
                            call_args[0][1] if len(call_args[0]) > 1 else None
                        )
                        break

                self.assertIsNotNone(
                    cancel_handler, "Cancel handler should be registered"
                )

                # Call the handler without job_id
                cancel_handler({})

                # Verify error was emitted
                mock_emit.assert_called_once()
                call_args = mock_emit.call_args
                self.assertEqual(call_args[0][0], "error")
                self.assertIn("Missing job_id", call_args[0][1]["message"])

    def test_cancel_job_handles_service_unavailable_gracefully(self):
        """Test cancel_job handles service unavailable gracefully.

        Requirements: 2.4
        """
        with patch(
            "api.websocket_events.get_socketio", return_value=self.mock_socketio
        ):
            with patch("api.websocket_events.emit") as mock_emit:
                with patch("api.websocket_events.current_app") as mock_current_app:
                    # Set up app context without job_service
                    mock_current_app.job_service = None

                    # Import and register events
                    from api.websocket_events import register_socketio_events

                    register_socketio_events(self.app)

                    # Get the registered cancel_job handler
                    cancel_handler = None
                    for call_args in self.mock_socketio.on.call_args_list:
                        if len(call_args[0]) > 0 and call_args[0][0] == "cancel_job":
                            cancel_handler = (
                                call_args[0][1] if len(call_args[0]) > 1 else None
                            )
                            break

                    self.assertIsNotNone(
                        cancel_handler, "Cancel handler should be registered"
                    )

                    # Call the handler with job_id
                    cancel_handler({"job_id": "job-999"})

                    # Verify error was emitted
                    mock_emit.assert_called()
                    call_args = mock_emit.call_args
                    self.assertEqual(call_args[0][0], "error")
                    self.assertIn("not initialized", call_args[0][1]["message"])


if __name__ == "__main__":
    unittest.main()
