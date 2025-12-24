"""
API v1 - UltraDL REST API

This module contains the versioned API endpoints with OpenAPI/Swagger documentation.
"""

import os

from flask import Blueprint
from flask_restx import Api

# Get API version from environment
API_VERSION = os.getenv("API_VERSION", "v1")

# Create blueprint for API v1
api_v1_bp = Blueprint("api_v1", __name__, url_prefix=f"/api/{API_VERSION}")

# Initialize Flask-RESTX API with Swagger documentation
api = Api(
    api_v1_bp,
    version="1.0",
    title="UltraDL API",
    description="YouTube video downloader API with support for multiple resolutions up to 8K",
    doc="/docs",  # Swagger UI will be available at /api/v1/docs
    contact="UltraDL Team",
    license="MIT",
    # No authentication required
)

# Import namespaces after api is created to avoid circular imports
from .namespaces import download_ns, job_ns, video_ns

# Register namespaces
api.add_namespace(video_ns, path="/videos")
api.add_namespace(job_ns, path="/jobs")
api.add_namespace(download_ns, path="/downloads")
