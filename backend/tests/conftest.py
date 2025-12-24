"""
Shared pytest fixtures and configuration for the UltraDL backend test suite.

This module provides:
- Hypothesis configuration for property-based testing
- Shared fixtures for domain entities and value objects
- Mock repository implementations
- Test utilities and assertion helpers

Requirements: 7.2, 8.1, 8.5, 9.1, 9.2
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import Mock

# Hypothesis configuration
from hypothesis import settings, HealthCheck, Phase

# Register Hypothesis profiles
settings.register_profile(
    "default",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target, Phase.shrink],
)
settings.register_profile(
    "ci",
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "dev",
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("default")


# =============================================================================
# Domain Entity Fixtures
# =============================================================================

@pytest.fixture
def sample_youtube_url() -> str:
    """Provide a sample valid YouTube URL."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def sample_format_id() -> str:
    """Provide a sample valid format ID."""
    return "best"


@pytest.fixture
def sample_download_token() -> str:
    """Provide a sample valid download token (32+ characters)."""
    return "test_token_" + "a" * 32


# =============================================================================
# Mock Repository Fixtures
# =============================================================================

@pytest.fixture
def mock_job_repository():
    """
    Provide a mock job repository for unit testing.
    
    Returns a Mock object with all JobRepository interface methods.
    """
    mock = Mock()
    mock.save.return_value = True
    mock.get.return_value = None
    mock.delete.return_value = True
    mock.update_progress.return_value = True
    mock.update_status.return_value = True
    mock.get_expired_jobs.return_value = []
    mock.exists.return_value = False
    mock.get_many.return_value = []
    mock.save_many.return_value = True
    mock.find_by_status.return_value = []
    return mock


@pytest.fixture
def mock_archive_repository():
    """
    Provide a mock archive repository for unit testing.
    
    Returns a Mock object with all IJobArchiveRepository interface methods.
    """
    mock = Mock()
    mock.save.return_value = True
    mock.get.return_value = None
    mock.get_by_date_range.return_value = []
    mock.count_by_status.return_value = 0
    return mock


@pytest.fixture
def mock_file_repository():
    """
    Provide a mock file repository for unit testing.
    
    Returns a Mock object with file repository interface methods.
    """
    mock = Mock()
    mock.save.return_value = True
    mock.get.return_value = None
    mock.delete.return_value = True
    mock.get_expired_files.return_value = []
    mock.delete_file_by_job_id.return_value = True
    return mock


@pytest.fixture
def mock_storage_repository():
    """
    Provide a mock storage repository for unit testing.
    
    Returns a Mock object with storage repository interface methods.
    """
    mock = Mock()
    mock.upload.return_value = True
    mock.download.return_value = b"test content"
    mock.delete.return_value = True
    mock.exists.return_value = False
    mock.generate_signed_url.return_value = "https://example.com/signed-url"
    return mock


@pytest.fixture
def mock_metadata_extractor():
    """
    Provide a mock metadata extractor for unit testing.
    
    Returns a Mock object with deterministic behavior.
    """
    mock = Mock()
    mock.extract_metadata.return_value = {
        "title": "Test Video",
        "duration": 180,
        "thumbnail": "https://example.com/thumb.jpg",
    }
    mock.extract_formats.return_value = [
        {"format_id": "best", "ext": "mp4", "resolution": "1080p"},
        {"format_id": "140", "ext": "m4a", "resolution": "audio only"},
    ]
    return mock


# =============================================================================
# Time-related Fixtures
# =============================================================================

@pytest.fixture
def fixed_datetime():
    """Provide a fixed datetime for deterministic testing."""
    return datetime(2024, 1, 15, 12, 0, 0)


@pytest.fixture
def expired_datetime():
    """Provide a datetime that represents an expired timestamp."""
    return datetime.utcnow() - timedelta(hours=2)


# =============================================================================
# Pytest Configuration Hooks
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require external services)"
    )
    config.addinivalue_line(
        "markers", "contract: Contract tests (verify interface compliance)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full workflows)"
    )
    config.addinivalue_line(
        "markers", "property: Property-based tests using Hypothesis"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically mark tests based on their location.
    
    - tests/unit/* -> @pytest.mark.unit
    - tests/integration/* -> @pytest.mark.integration
    - tests/contracts/* -> @pytest.mark.contract
    - tests/e2e/* -> @pytest.mark.e2e
    - tests/property/* -> @pytest.mark.property
    """
    for item in items:
        # Get the test file path relative to tests directory
        test_path = str(item.fspath)
        
        if "/unit/" in test_path or "\\unit\\" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path or "\\integration\\" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/contracts/" in test_path or "\\contracts\\" in test_path:
            item.add_marker(pytest.mark.contract)
        elif "/e2e/" in test_path or "\\e2e\\" in test_path:
            item.add_marker(pytest.mark.e2e)
        elif "/property/" in test_path or "\\property\\" in test_path:
            item.add_marker(pytest.mark.property)
