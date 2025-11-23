"""
Event Handlers (Deprecated)

This module is deprecated. Import from infrastructure.event_handlers package instead.
Kept for backward compatibility.
"""

# Re-export from new location for backward compatibility
from infrastructure.event_handlers.logging_handler import LoggingEventHandler
from infrastructure.event_handlers.websocket_handler import WebSocketEventHandler

__all__ = [
    "LoggingEventHandler",
    "WebSocketEventHandler",
]
