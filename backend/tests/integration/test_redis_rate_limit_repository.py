"""
Redis Rate Limit Repository Integration Tests

Tests Redis integration for rate limiting including atomic operations,
TTL management, key generation, and graceful degradation.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.1, 8.2, 8.3, 12.1, 12.2, 12.3, 12.4
"""

import os
import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import redis

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_client
from infrastructure.redis_rate_limit_repository import RedisRateLimitRepository
from domain.rate_limiting.value_objects import ClientIP, RateLimit


# Test data
TEST_IP = "192.168.1.100"
TEST_IP_V6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"


@pytest.fixture
def redis_client():
    """Fixture to provide Redis client instance."""
    init_redis()
    client = get_redis_client()
    
    yield client
    
    # Cleanup: flush test keys
    # Use pattern matching to delete only rate limit keys
    for key in client.scan_iter(match="ratelimit:*"):
        client.delete(key)


@pytest.fixture
def repository(redis_client):
    """Fixture to provide RedisRateLimitRepository instance."""
    return RedisRateLimitRepository(redis_client, timeout=1)


@pytest.mark.integration
def test_redis_key_format_generation(repository):
    """Test Redis key format generation (Requirement 2.4)."""
    client_ip = ClientIP(TEST_IP)
    limit_type = "daily_video-only"
    
    # Generate key
    key = repository._make_key(client_ip, limit_type)
    
    # Verify key format: ratelimit:{limit_type}:{ip_hash}
    assert key.startswith("ratelimit:")
    assert limit_type in key
    
    # Verify IP hash is included
    ip_hash = client_ip.hash_for_key()
    assert ip_hash in key
    
    # Verify complete format
    expected_key = f"ratelimit:{limit_type}:{ip_hash}"
    assert key == expected_key


@pytest.mark.integration
def test_redis_key_uniqueness_per_ip(repository):
    """Test that different IPs generate different keys (Requirement 2.4)."""
    ip1 = ClientIP("192.168.1.100")
    ip2 = ClientIP("192.168.1.101")
    limit_type = "daily_total"
    
    key1 = repository._make_key(ip1, limit_type)
    key2 = repository._make_key(ip2, limit_type)
    
    # Different IPs should have different keys
    assert key1 != key2


@pytest.mark.integration
def test_redis_key_uniqueness_per_limit_type(repository):
    """Test that different limit types generate different keys (Requirement 2.4)."""
    client_ip = ClientIP(TEST_IP)
    
    key_daily = repository._make_key(client_ip, "daily_video-only")
    key_hourly = repository._make_key(client_ip, "endpoint_hourly:/api/v1/videos/resolutions")
    key_minute = repository._make_key(client_ip, "per_minute")
    
    # Different limit types should have different keys
    assert key_daily != key_hourly
    assert key_daily != key_minute
    assert key_hourly != key_minute


@pytest.mark.integration
def test_get_limit_state_new_counter(repository):
    """Test get_limit_state() for new counter (Requirement 2.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Get state for non-existent counter
    entity = repository.get_limit_state(client_ip, rate_limit)
    
    # Verify initial state
    assert entity.client_ip == client_ip
    assert entity.limit_type == rate_limit.limit_type
    assert entity.current_count == 0
    assert entity.limit == rate_limit.limit
    assert entity.reset_at > datetime.utcnow()


@pytest.mark.integration
def test_get_limit_state_existing_counter(repository):
    """Test get_limit_state() retrieves correct count (Requirement 2.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Increment counter multiple times
    repository.increment(client_ip, rate_limit)
    repository.increment(client_ip, rate_limit)
    repository.increment(client_ip, rate_limit)
    
    # Get state
    entity = repository.get_limit_state(client_ip, rate_limit)
    
    # Verify count
    assert entity.current_count == 3
    assert entity.limit == 20


@pytest.mark.integration
def test_get_limit_state_retrieves_ttl(repository):
    """Test get_limit_state() retrieves correct TTL (Requirement 2.5)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=10, window_seconds=60, limit_type="per_minute")
    
    # Increment to set TTL
    repository.increment(client_ip, rate_limit)
    
    # Get state
    entity = repository.get_limit_state(client_ip, rate_limit)
    
    # Verify reset time is in the future
    assert entity.reset_at > datetime.utcnow()
    
    # Verify reset time is within expected window (with tolerance)
    expected_max = datetime.utcnow() + timedelta(seconds=rate_limit.window_seconds + 5)
    assert entity.reset_at <= expected_max


@pytest.mark.integration
def test_increment_atomically_increments_counter(repository):
    """Test increment() atomically increments counter (Requirement 2.2, 8.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # First increment
    entity1 = repository.increment(client_ip, rate_limit)
    assert entity1.current_count == 1
    
    # Second increment
    entity2 = repository.increment(client_ip, rate_limit)
    assert entity2.current_count == 2
    
    # Third increment
    entity3 = repository.increment(client_ip, rate_limit)
    assert entity3.current_count == 3


@pytest.mark.integration
def test_increment_sets_expireat_on_first_increment(repository, redis_client):
    """Test increment() sets EXPIREAT on first increment (Requirement 8.2)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # First increment
    entity = repository.increment(client_ip, rate_limit)
    
    # Verify TTL is set
    key = repository._make_key(client_ip, rate_limit.limit_type)
    ttl = redis_client.ttl(key)
    
    # TTL should be positive (key has expiration)
    assert ttl > 0
    
    # TTL should be close to window_seconds (allow some tolerance)
    assert ttl <= rate_limit.window_seconds


@pytest.mark.integration
def test_increment_maintains_expireat_on_subsequent_increments(repository, redis_client):
    """Test increment() maintains EXPIREAT on subsequent increments (Requirement 8.2)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # First increment
    repository.increment(client_ip, rate_limit)
    
    # Get initial TTL
    key = repository._make_key(client_ip, rate_limit.limit_type)
    initial_ttl = redis_client.ttl(key)
    
    # Wait a moment
    time.sleep(1)
    
    # Second increment
    repository.increment(client_ip, rate_limit)
    
    # Get new TTL
    new_ttl = redis_client.ttl(key)
    
    # TTL should still be set and close to initial value (decreased by ~1 second)
    assert new_ttl > 0
    assert abs(new_ttl - (initial_ttl - 1)) <= 2  # Allow 2 second tolerance


@pytest.mark.integration
def test_reset_counter_deletes_redis_key(repository, redis_client):
    """Test reset_counter() deletes Redis key (Requirement 8.3)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Increment counter
    repository.increment(client_ip, rate_limit)
    
    # Verify key exists
    key = repository._make_key(client_ip, rate_limit.limit_type)
    assert redis_client.exists(key) == 1
    
    # Reset counter
    result = repository.reset_counter(client_ip, rate_limit.limit_type)
    
    # Verify success
    assert result is True
    
    # Verify key is deleted
    assert redis_client.exists(key) == 0


@pytest.mark.integration
def test_reset_counter_nonexistent_key(repository):
    """Test reset_counter() on non-existent key returns False (Requirement 8.3)."""
    client_ip = ClientIP(TEST_IP)
    limit_type = "daily_video-only"
    
    # Reset non-existent counter
    result = repository.reset_counter(client_ip, limit_type)
    
    # Should return False (no key deleted)
    assert result is False


@pytest.mark.integration
def test_ttl_calculation_for_daily_limits(repository):
    """Test TTL calculation for daily limits (Requirement 8.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Calculate reset time
    reset_time = repository._calculate_reset_time(rate_limit)
    
    # Verify reset time is next midnight UTC
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    expected_midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    
    assert reset_time == expected_midnight


@pytest.mark.integration
def test_ttl_calculation_for_hourly_limits(repository):
    """Test TTL calculation for hourly limits (Requirement 8.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(
        limit=100,
        window_seconds=3600,
        limit_type="endpoint_hourly:/api/v1/videos/resolutions"
    )
    
    # Calculate reset time
    reset_time = repository._calculate_reset_time(rate_limit)
    
    # Verify reset time is next hour boundary
    now = datetime.utcnow()
    next_hour = now + timedelta(hours=1)
    expected_hour = datetime(next_hour.year, next_hour.month, next_hour.day, next_hour.hour, 0, 0)
    
    assert reset_time == expected_hour


@pytest.mark.integration
def test_ttl_calculation_for_per_minute_limits(repository):
    """Test TTL calculation for per-minute limits (Requirement 8.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=10, window_seconds=60, limit_type="per_minute")
    
    # Calculate reset time
    reset_time = repository._calculate_reset_time(rate_limit)
    
    # Verify reset time is next minute boundary
    now = datetime.utcnow()
    next_minute = now + timedelta(minutes=1)
    expected_minute = datetime(
        next_minute.year, next_minute.month, next_minute.day,
        next_minute.hour, next_minute.minute, 0
    )
    
    assert reset_time == expected_minute


@pytest.mark.integration
def test_ipv6_address_support(repository):
    """Test IPv6 address support (Requirement 2.1)."""
    client_ip = ClientIP(TEST_IP_V6)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Increment counter
    entity = repository.increment(client_ip, rate_limit)
    
    # Verify operation succeeded
    assert entity.current_count == 1
    assert entity.client_ip.address == TEST_IP_V6
    
    # Get state
    entity2 = repository.get_limit_state(client_ip, rate_limit)
    assert entity2.current_count == 1


@pytest.mark.integration
def test_multiple_limit_types_independent(repository):
    """Test multiple limit types are tracked independently (Requirement 2.1)."""
    client_ip = ClientIP(TEST_IP)
    
    # Create different rate limits
    daily_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    hourly_limit = RateLimit(limit=100, window_seconds=3600, limit_type="endpoint_hourly:/api/v1/videos/resolutions")
    minute_limit = RateLimit(limit=10, window_seconds=60, limit_type="per_minute")
    
    # Increment each counter
    repository.increment(client_ip, daily_limit)
    repository.increment(client_ip, daily_limit)
    
    repository.increment(client_ip, hourly_limit)
    repository.increment(client_ip, hourly_limit)
    repository.increment(client_ip, hourly_limit)
    
    repository.increment(client_ip, minute_limit)
    
    # Verify each counter is independent
    daily_entity = repository.get_limit_state(client_ip, daily_limit)
    hourly_entity = repository.get_limit_state(client_ip, hourly_limit)
    minute_entity = repository.get_limit_state(client_ip, minute_limit)
    
    assert daily_entity.current_count == 2
    assert hourly_entity.current_count == 3
    assert minute_entity.current_count == 1



# ============================================================================
# Graceful Degradation Tests
# ============================================================================


@pytest.mark.integration
def test_redis_connection_failure_returns_unlimited_entity(repository):
    """Test Redis connection failure returns unlimited entity (Requirement 12.1, 12.2)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.ConnectionError("Connection refused")
        
        # Get limit state should not raise exception
        entity = repository.get_limit_state(client_ip, rate_limit)
        
        # Verify unlimited entity returned
        assert entity.current_count == 0
        assert entity.limit == rate_limit.limit
        assert not entity.is_exceeded()


@pytest.mark.integration
def test_redis_timeout_returns_unlimited_entity(repository):
    """Test Redis timeout returns unlimited entity (Requirement 12.3)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise TimeoutError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.TimeoutError("Operation timed out")
        
        # Get limit state should not raise exception
        entity = repository.get_limit_state(client_ip, rate_limit)
        
        # Verify unlimited entity returned
        assert entity.current_count == 0
        assert not entity.is_exceeded()


@pytest.mark.integration
def test_redis_error_logging_on_connection_failure(repository, caplog):
    """Test error logging on Redis connection failure (Requirement 12.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.ConnectionError("Connection refused")
        
        # Trigger error
        with caplog.at_level('ERROR'):
            entity = repository.get_limit_state(client_ip, rate_limit)
        
        # Verify error was logged
        assert any("Redis error in get_limit_state" in record.message for record in caplog.records)


@pytest.mark.integration
def test_increment_connection_failure_returns_unlimited_entity(repository):
    """Test increment() with connection failure returns unlimited entity (Requirement 12.2)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.ConnectionError("Connection refused")
        
        # Increment should not raise exception
        entity = repository.increment(client_ip, rate_limit)
        
        # Verify unlimited entity returned
        assert entity.current_count == 0
        assert not entity.is_exceeded()


@pytest.mark.integration
def test_increment_timeout_returns_unlimited_entity(repository):
    """Test increment() with timeout returns unlimited entity (Requirement 12.3)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise TimeoutError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.TimeoutError("Operation timed out")
        
        # Increment should not raise exception
        entity = repository.increment(client_ip, rate_limit)
        
        # Verify unlimited entity returned
        assert entity.current_count == 0


@pytest.mark.integration
def test_increment_error_logging(repository, caplog):
    """Test error logging on increment failure (Requirement 12.1)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.ConnectionError("Connection refused")
        
        # Trigger error
        with caplog.at_level('ERROR'):
            entity = repository.increment(client_ip, rate_limit)
        
        # Verify error was logged
        assert any("Redis error in increment" in record.message for record in caplog.records)


@pytest.mark.integration
def test_reset_counter_connection_failure_returns_false(repository):
    """Test reset_counter() with connection failure returns False (Requirement 12.2)."""
    client_ip = ClientIP(TEST_IP)
    limit_type = "daily_video-only"
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'delete') as mock_delete:
        mock_delete.side_effect = redis.ConnectionError("Connection refused")
        
        # Reset should not raise exception
        result = repository.reset_counter(client_ip, limit_type)
        
        # Verify False returned
        assert result is False


@pytest.mark.integration
def test_reset_counter_error_logging(repository, caplog):
    """Test error logging on reset_counter failure (Requirement 12.1)."""
    client_ip = ClientIP(TEST_IP)
    limit_type = "daily_video-only"
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'delete') as mock_delete:
        mock_delete.side_effect = redis.ConnectionError("Connection refused")
        
        # Trigger error
        with caplog.at_level('ERROR'):
            result = repository.reset_counter(client_ip, limit_type)
        
        # Verify error was logged
        assert any("Redis error in reset_counter" in record.message for record in caplog.records)


@pytest.mark.integration
def test_service_continues_when_redis_unavailable(repository):
    """Test service continues when Redis unavailable (Requirement 12.4)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise ConnectionError
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = redis.ConnectionError("Connection refused")
        
        # Multiple operations should all succeed (return unlimited entities)
        entity1 = repository.get_limit_state(client_ip, rate_limit)
        entity2 = repository.increment(client_ip, rate_limit)
        entity3 = repository.get_limit_state(client_ip, rate_limit)
        
        # All should return unlimited entities
        assert not entity1.is_exceeded()
        assert not entity2.is_exceeded()
        assert not entity3.is_exceeded()


@pytest.mark.integration
def test_unexpected_error_graceful_degradation(repository, caplog):
    """Test graceful degradation on unexpected errors (Requirement 12.2)."""
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # Mock Redis to raise unexpected exception
    with patch.object(repository.redis, 'pipeline') as mock_pipeline:
        mock_pipeline.side_effect = Exception("Unexpected error")
        
        # Should not raise exception
        with caplog.at_level('ERROR'):
            entity = repository.get_limit_state(client_ip, rate_limit)
        
        # Verify unlimited entity returned
        assert entity.current_count == 0
        assert not entity.is_exceeded()
        
        # Verify error was logged
        assert any("Unexpected error in get_limit_state" in record.message for record in caplog.records)


@pytest.mark.integration
def test_timeout_configuration(redis_client):
    """Test timeout configuration is respected (Requirement 12.3)."""
    # Create repository with custom timeout
    custom_timeout = 2
    repository = RedisRateLimitRepository(redis_client, timeout=custom_timeout)
    
    # Verify timeout is set
    assert repository.timeout == custom_timeout
    
    # Test that timeout is applied to operations
    client_ip = ClientIP(TEST_IP)
    rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily_video-only")
    
    # This should work normally
    entity = repository.increment(client_ip, rate_limit)
    assert entity.current_count == 1
