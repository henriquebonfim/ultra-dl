
import pytest
import datetime
from src.infrastructure.redis_cache_service import RedisCacheService
from src.infrastructure.redis_repository import RedisRepository

@pytest.mark.integration
class TestRedisCacheIntegration:
    """Integration tests for RedisCacheService using real Redis."""

    @pytest.fixture
    def cache_service(self, redis_client):
        """Create cache service instance (wrapping RedisRepository)."""
        # RedisCacheService expects a RedisRepository instance, not raw client
        redis_repo = RedisRepository(redis_client)
        return RedisCacheService(redis_repo)

    def test_metadata_caching_cycle(self, cache_service):
        """Verify setting and getting video metadata."""
        # Arrange
        url = "https://youtube.com/watch?v=cache_test"
        metadata = {
            "title": "Cached Video",
            "duration": 500,
            "uploader": "Test Uploader"
        }

        # Act - Set
        result = cache_service.set_video_metadata(url, metadata)
        assert result is True

        # Act - Get
        cached_data = cache_service.get_video_metadata(url)

        # Assert
        assert cached_data is not None
        assert cached_data["title"] == "Cached Video"
        assert cached_data["duration"] == 500

    def test_format_caching_cycle(self, cache_service):
        """Verify setting and getting format info."""
        # Arrange
        url = "https://youtube.com/watch?v=format_test"
        formats = {
            "formats": [
                {"format_id": "best", "ext": "mp4"},
                {"format_id": "140", "ext": "m4a"}
            ]
        }

        # Act
        cache_service.set_format_info(url, formats, ttl=60)
        cached_formats = cache_service.get_format_info(url)

        # Assert
        assert cached_formats is not None
        assert len(cached_formats["formats"]) == 2
        assert cached_formats["formats"][0]["format_id"] == "best"

    def test_cache_miss(self, cache_service):
        """Verify None is returned for non-existent keys."""
        # Act
        result = cache_service.get_video_metadata("https://youtube.com/watch?v=ghost")

        # Assert
        assert result is None

    def test_ttl_behavior(self, cache_service):
        """Verify items expire (using low level check since we can't wait minutes)."""
        # Arrange
        url = "https://youtube.com/watch?v=ttl_test"
        metadata = {"foo": "bar"}
        ttl = 100

        # Act
        cache_service.set_video_metadata(url, metadata, ttl=ttl)

        # Assert
        key = cache_service._make_metadata_key(url)
        actual_ttl = cache_service.redis_repo.redis.ttl(cache_service.redis_repo._make_key(key))

        # Redis TTL might be slightly less than set value immediately
        assert 0 < actual_ttl <= 100
