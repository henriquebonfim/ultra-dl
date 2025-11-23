"""
Redis Cache Service Integration Tests

Tests cache hit/miss behavior, TTL expiration, and cache key generation.
Verifies that caching reduces yt-dlp calls and maintains data integrity.

Requirements: 1.5, 2.3
"""

import os
import time
import hashlib
import pytest
from unittest.mock import Mock, patch

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_repository
from infrastructure.redis_cache_service import RedisCacheService
from application.video_service import VideoService


# Test data
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
TEST_METADATA = {
    "id": "dQw4w9WgXcQ",
    "title": "Test Video",
    "uploader": "Test Channel",
    "duration": 212,
    "thumbnail": "https://example.com/thumb.jpg"
}
TEST_FORMATS = [
    {
        "format_id": "18",
        "ext": "mp4",
        "resolution": "360p",
        "filesize": 5242880,
        "format_type": "video_with_audio"
    },
    {
        "format_id": "22",
        "ext": "mp4",
        "resolution": "720p",
        "filesize": 15728640,
        "format_type": "video_with_audio"
    }
]


@pytest.fixture
def cache_service():
    """Fixture to provide cache service instance."""
    init_redis()
    redis_repo = get_redis_repository("test_cache")
    service = RedisCacheService(redis_repo, default_ttl=300)
    
    yield service
    
    # Cleanup after test
    metadata_key = service._make_metadata_key(TEST_URL)
    formats_key = service._make_formats_key(TEST_URL)
    redis_repo.delete(metadata_key)
    redis_repo.delete(formats_key)


@pytest.mark.integration
def test_cache_key_generation(cache_service):
    """Test cache key generation uses SHA-256 hashing (Requirement 1.5)."""
    # Generate keys
    metadata_key = cache_service._make_metadata_key(TEST_URL)
    formats_key = cache_service._make_formats_key(TEST_URL)
    
    # Verify key format
    expected_hash = hashlib.sha256(TEST_URL.encode('utf-8')).hexdigest()
    expected_metadata_key = f"video:metadata:{expected_hash}"
    expected_formats_key = f"video:formats:{expected_hash}"
    
    assert metadata_key == expected_metadata_key
    assert formats_key == expected_formats_key


@pytest.mark.integration
def test_cache_key_collision_resistance(cache_service):
    """Test that different URLs generate different cache keys (Requirement 1.5)."""
    url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url2 = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    url3 = "https://youtu.be/dQw4w9WgXcQ"  # Different format, same video
    
    key1 = cache_service._make_metadata_key(url1)
    key2 = cache_service._make_metadata_key(url2)
    key3 = cache_service._make_metadata_key(url3)
    
    # Different videos should have different keys
    assert key1 != key2
    
    # Different URL formats for same video should have different keys
    # (This is expected behavior - URL normalization would be a separate feature)
    assert key1 != key3


@pytest.mark.integration
def test_set_and_get_video_metadata(cache_service):
    """Test setting and retrieving video metadata from cache (Requirement 1.5)."""
    # Set metadata
    success = cache_service.set_video_metadata(TEST_URL, TEST_METADATA)
    assert success
    
    # Get metadata
    cached_data = cache_service.get_video_metadata(TEST_URL)
    assert cached_data is not None
    assert cached_data == TEST_METADATA


@pytest.mark.integration
def test_set_and_get_format_info(cache_service):
    """Test setting and retrieving format info from cache (Requirement 1.5)."""
    # Set formats
    success = cache_service.set_format_info(TEST_URL, TEST_FORMATS)
    assert success
    
    # Get formats
    cached_formats = cache_service.get_format_info(TEST_URL)
    assert cached_formats is not None
    assert cached_formats == TEST_FORMATS


@pytest.mark.integration
def test_cache_miss_returns_none(cache_service):
    """Test that cache miss returns None (Requirement 1.5)."""
    # Try to get non-existent metadata
    cached_metadata = cache_service.get_video_metadata(TEST_URL)
    assert cached_metadata is None
    
    # Try to get non-existent formats
    cached_formats = cache_service.get_format_info(TEST_URL)
    assert cached_formats is None


@pytest.mark.integration
def test_ttl_expiration(cache_service):
    """Test that cached data expires after TTL (Requirement 1.5)."""
    # Set metadata with short TTL (2 seconds)
    short_ttl = 2
    success = cache_service.set_video_metadata(TEST_URL, TEST_METADATA, ttl=short_ttl)
    assert success
    
    # Verify data is cached
    cached_data = cache_service.get_video_metadata(TEST_URL)
    assert cached_data is not None
    
    # Wait for TTL to expire
    time.sleep(short_ttl + 1)
    
    # Verify data has expired
    expired_data = cache_service.get_video_metadata(TEST_URL)
    assert expired_data is None


@pytest.mark.integration
def test_custom_ttl_overrides_default(cache_service):
    """Test that custom TTL overrides default TTL (Requirement 1.5)."""
    # Set with custom TTL
    custom_ttl = 10
    success = cache_service.set_video_metadata(TEST_URL, TEST_METADATA, ttl=custom_ttl)
    assert success
    
    # Check TTL in Redis
    metadata_key = cache_service._make_metadata_key(TEST_URL)
    redis_key = cache_service.redis_repo._make_key(metadata_key)
    actual_ttl = cache_service.redis_repo.redis.ttl(redis_key)
    
    # TTL should be close to custom value (allow 1 second tolerance)
    assert abs(actual_ttl - custom_ttl) <= 1


@pytest.mark.integration
def test_cache_hit_reduces_yt_dlp_calls(cache_service):
    """Test that cache hit reduces yt-dlp calls (Requirement 2.3)."""
    # Create VideoService with cache
    video_service = VideoService(cache_service=cache_service)
    
    # Mock the VideoProcessor to avoid actual yt-dlp calls
    with patch.object(video_service.video_processor, 'extract_metadata') as mock_extract, \
         patch.object(video_service.video_processor, 'get_available_formats') as mock_formats, \
         patch.object(video_service.video_processor, 'formats_to_frontend_list') as mock_format_list:
        
        # Configure mocks
        mock_metadata = Mock()
        mock_metadata.id = TEST_METADATA["id"]
        mock_metadata.title = TEST_METADATA["title"]
        mock_metadata.uploader = TEST_METADATA["uploader"]
        mock_metadata.duration = TEST_METADATA["duration"]
        mock_metadata.thumbnail = TEST_METADATA["thumbnail"]
        
        mock_extract.return_value = mock_metadata
        mock_formats.return_value = []
        mock_format_list.return_value = TEST_FORMATS
        
        # First call - should hit yt-dlp and cache
        result1 = video_service.get_video_info(TEST_URL)
        
        assert mock_extract.call_count == 1
        assert mock_formats.call_count == 1
        
        # Second call - should hit cache, no yt-dlp calls
        result2 = video_service.get_video_info(TEST_URL)
        
        assert mock_extract.call_count == 1
        assert mock_formats.call_count == 1
        
        # Verify results are identical
        assert result1 == result2


@pytest.mark.integration
def test_cache_miss_triggers_yt_dlp_and_updates_cache(cache_service):
    """Test that cache miss triggers yt-dlp and updates cache (Requirement 2.3)."""
    # Create VideoService with cache
    video_service = VideoService(cache_service=cache_service)
    
    # Mock the VideoProcessor
    with patch.object(video_service.video_processor, 'extract_metadata') as mock_extract, \
         patch.object(video_service.video_processor, 'get_available_formats') as mock_formats, \
         patch.object(video_service.video_processor, 'formats_to_frontend_list') as mock_format_list:
        
        # Configure mocks
        mock_metadata = Mock()
        mock_metadata.id = TEST_METADATA["id"]
        mock_metadata.title = TEST_METADATA["title"]
        mock_metadata.uploader = TEST_METADATA["uploader"]
        mock_metadata.duration = TEST_METADATA["duration"]
        mock_metadata.thumbnail = TEST_METADATA["thumbnail"]
        
        mock_extract.return_value = mock_metadata
        mock_formats.return_value = []
        mock_format_list.return_value = TEST_FORMATS
        
        # Verify cache is empty
        cached_before = cache_service.get_video_metadata(TEST_URL)
        assert cached_before is None
        
        # Call service - should trigger yt-dlp
        result = video_service.get_video_info(TEST_URL)
        
        assert mock_extract.call_count == 1
        assert mock_formats.call_count == 1
        
        # Verify cache is now populated
        cached_metadata = cache_service.get_video_metadata(TEST_URL)
        cached_formats = cache_service.get_format_info(TEST_URL)
        
        assert cached_metadata is not None
        assert cached_formats is not None
        assert cached_metadata["title"] == TEST_METADATA["title"]
        assert len(cached_formats) == len(TEST_FORMATS)


@pytest.mark.integration
def test_partial_cache_hit(cache_service):
    """Test behavior when only metadata or formats are cached (Requirement 2.3)."""
    # Cache only metadata, not formats
    cache_service.set_video_metadata(TEST_URL, TEST_METADATA)
    
    # Create VideoService with cache
    video_service = VideoService(cache_service=cache_service)
    
    # Mock the VideoProcessor
    with patch.object(video_service.video_processor, 'extract_metadata') as mock_extract, \
         patch.object(video_service.video_processor, 'get_available_formats') as mock_formats, \
         patch.object(video_service.video_processor, 'formats_to_frontend_list') as mock_format_list:
        
        mock_formats.return_value = []
        mock_format_list.return_value = TEST_FORMATS
        
        # Call service
        result = video_service.get_video_info(TEST_URL)
        
        # Metadata should come from cache (no extraction)
        assert mock_extract.call_count == 0
        
        # Formats should be fetched from yt-dlp
        assert mock_formats.call_count == 1
        
        # Verify both are now cached
        cached_formats = cache_service.get_format_info(TEST_URL)
        assert cached_formats is not None
