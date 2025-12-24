"""
main.py

Flask backend with Celery integration for asynchronous YouTube downloading.
This version integrates Redis for job persistence and Celery for background processing.

Dependencies:
  - Python packages: Flask, yt-dlp, flask-cors, redis, celery
  - System: ffmpeg (must be on PATH for merging/processing)
  - Infrastructure: Redis server

Notes:
  - Uses Redis for job persistence and Celery for async processing
  - API v1 endpoints available at /api/v1/ with Swagger docs at /api/v1/docs
  - Uses application factory pattern for better testability
"""

import os

from app_factory import create_app
from src.config.socketio_config import get_socketio, is_socketio_enabled

app = create_app()

if __name__ == "__main__":
    # Run on port 8000 (Replit allowed port) to avoid conflict with Vite frontend on 5000
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # Use SocketIO.run if available, otherwise fall back to app.run
    if is_socketio_enabled():
        from src.config.socketio_config import get_socketio

        socketio = get_socketio()
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=debug)
