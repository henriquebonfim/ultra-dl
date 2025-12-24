"""
SocketIO Configuration

Configures Flask-SocketIO with Redis message queue for WebSocket support.
"""

import logging
import os

from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio = None


def init_socketio(app):
    """
    Initialize Flask-SocketIO with Redis message queue.

    Args:
        app: Flask application instance

    Returns:
        SocketIO instance
    """
    global socketio

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Initialize SocketIO with Redis message queue for multi-worker support
        socketio = SocketIO(
            app,
            cors_allowed_origins="*",  # Configure based on environment
            message_queue=redis_url,
            async_mode="gevent",
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25,
        )

        logger.info(f"SocketIO initialized with Redis message queue: {redis_url}")
        return socketio

    except Exception as e:
        logger.error(f"Failed to initialize SocketIO: {e}")
        raise


def get_socketio():
    """
    Get the global SocketIO instance.

    Returns:
        SocketIO instance or None if not initialized
    """
    return socketio


def is_socketio_enabled():
    """
    Check if SocketIO is enabled and initialized.

    Returns:
        bool: True if SocketIO is available
    """
    socketio_enabled = os.getenv("SOCKETIO_ENABLED", "true").lower() == "true"
    return socketio_enabled and socketio is not None
