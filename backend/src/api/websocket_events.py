"""
WebSocket Event Handlers

Handles WebSocket connections and events for real-time progress updates.
"""

import logging

from flask import request
from flask_socketio import emit, join_room, leave_room

from src.config.socketio_config import get_socketio

logger = logging.getLogger(__name__)


def register_socketio_events(app):
    """
    Register WebSocket event handlers with the Flask-SocketIO instance.

    Args:
        app: Flask application instance
    """
    socketio = get_socketio()

    if socketio is None:
        logger.warning("SocketIO not initialized, skipping event registration")
        return

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection."""
        client_id = request.sid
        logger.info(f"Client connected: {client_id}")
        emit("connected", {"message": "Connected to server", "client_id": client_id})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection."""
        client_id = request.sid
        logger.info(f"Client disconnected: {client_id}")

    @socketio.on("subscribe_job")
    def handle_subscribe_job(data):
        """
        Subscribe to job progress updates.

        Args:
            data: dict with 'job_id' field
        """
        job_id = data.get("job_id")

        if not job_id:
            emit("error", {"message": "Missing job_id"})
            return

        # Join room for this job
        join_room(job_id)
        client_id = request.sid

        logger.info(f"Client {client_id} subscribed to job {job_id}")
        emit("subscribed", {"job_id": job_id, "message": f"Subscribed to job {job_id}"})

    @socketio.on("unsubscribe_job")
    def handle_unsubscribe_job(data):
        """
        Unsubscribe from job progress updates.

        Args:
            data: dict with 'job_id' field
        """
        job_id = data.get("job_id")

        if not job_id:
            emit("error", {"message": "Missing job_id"})
            return

        # Leave room for this job
        leave_room(job_id)
        client_id = request.sid

        logger.info(f"Client {client_id} unsubscribed from job {job_id}")
        emit(
            "unsubscribed",
            {"job_id": job_id, "message": f"Unsubscribed from job {job_id}"},
        )

    @socketio.on("ping")
    def handle_ping():
        """Handle ping from client for connection health check."""
        emit("pong", {"timestamp": request.args.get("timestamp")})

    @socketio.on("cancel_job")
    def handle_cancel_job(data):
        """
        Cancel a pending or processing job.

        Args:
            data: dict with 'job_id' field
        """
        from flask import current_app

        job_id = data.get("job_id")

        if not job_id:
            emit("error", {"message": "Missing job_id"})
            return

        try:
            # Get job_service from app context
            job_service = current_app.job_service
            if not job_service:
                emit("error", {"message": "Job service not initialized"})
                return

            # Delete the job (which will also delete the file if it exists)
            success = job_service.delete_job(job_id)

            if success:
                client_id = request.sid
                logger.info(f"Client {client_id} cancelled job {job_id}")
                emit(
                    "job_cancelled",
                    {
                        "job_id": job_id,
                        "message": f"Job {job_id} cancelled successfully",
                    },
                )

                # Broadcast cancellation to all subscribers
                socketio.emit("job_cancelled", {"job_id": job_id}, room=job_id)
            else:
                emit("error", {"message": f"Failed to cancel job {job_id}"})

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {str(e)}")
            emit("error", {"message": f"Error cancelling job: {str(e)}"})

    logger.info("SocketIO event handlers registered")


def emit_job_progress(job_id, progress_data):
    """
    Emit job progress update to all subscribed clients.

    Args:
        job_id: Job identifier
        progress_data: Progress information dict
    """
    socketio = get_socketio()

    if socketio is None:
        return

    try:
        # Emit to all clients in the job's room
        socketio.emit(
            "job_progress", {"job_id": job_id, "progress": progress_data}, room=job_id
        )

        logger.debug(f"Emitted progress update for job {job_id}: {progress_data}")

    except Exception as e:
        logger.error(f"Failed to emit progress for job {job_id}: {e}")


def emit_job_completed(job_id, download_url, expire_at=None):
    """
    Emit job completion event to all subscribed clients.

    Args:
        job_id: Job identifier
        download_url: Download URL for completed job
        expire_at: When the download URL expires (datetime)
    """
    socketio = get_socketio()

    if socketio is None:
        return

    try:
        # Prepare event data
        event_data = {
            "job_id": job_id,
            "status": "completed",
            "download_url": download_url,
        }

        # Add expire_at if provided
        if expire_at is not None:
            event_data["expire_at"] = expire_at.isoformat()

        # Emit to all clients in the job's room
        socketio.emit(
            "job_completed",
            event_data,
            room=job_id,
        )

        logger.info(f"Emitted completion event for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to emit completion for job {job_id}: {e}")


def emit_job_failed(job_id, error_message, error_category=None):
    """
    Emit job failure event to all subscribed clients.

    Args:
        job_id: Job identifier
        error_message: Error message
        error_category: Error category for better user experience
    """
    socketio = get_socketio()

    if socketio is None:
        return

    try:
        # Emit to all clients in the job's room
        event_data = {"job_id": job_id, "status": "failed", "error": error_message}

        if error_category:
            event_data["error_category"] = error_category

        socketio.emit("job_failed", event_data, room=job_id)

        logger.info(f"Emitted failure event for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to emit failure for job {job_id}: {e}")


def emit_job_cancelled(job_id):
    """
    Emit job cancellation event to all subscribed clients.

    Args:
        job_id: Job identifier
    """
    socketio = get_socketio()

    if socketio is None:
        return

    try:
        # Emit to all clients in the job's room
        socketio.emit(
            "job_cancelled", {"job_id": job_id, "status": "cancelled"}, room=job_id
        )

        logger.info(f"Emitted cancellation event for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to emit cancellation for job {job_id}: {e}")


def emit_job_warning(job_id, message):
    """
    Emit job warning event to all subscribed clients.

    Args:
        job_id: Job identifier
        message: Warning message to display to the user
    """
    socketio = get_socketio()

    if socketio is None:
        return

    try:
        # Emit to all clients in the job's room
        socketio.emit(
            "job_warning", {"job_id": job_id, "message": message}, room=job_id
        )

        logger.info(f"Emitted warning event for job {job_id}: {message}")

    except Exception as e:
        logger.error(f"Failed to emit warning for job {job_id}: {e}")
