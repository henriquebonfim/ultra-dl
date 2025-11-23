"""
Rate Limit Service Integration Tests

Tests application service orchestration logic for rate limiting including
multiple limit checks, production-only enforcement, and most restrictive
entity selection.

Requirements: 1.1, 1.2, 3.1, 3.2, 3.3, 4.1, 4.2, 4.4, 5.1, 5.3, 5.4, 6.1, 6.3, 6.4
"""

import os
import pytest
from unittest.mock import Mock, patch

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_client
from application.rate_limit_service import RateLimitService
from domain.rate_limiting.services import RateLimitManager
from domain.rate_limiting.value_objects import ClientIP, RateLimit
from domain.errors import RateLimitExceededError
from infrastructure.redis_rate_limit_repository import RedisRateLimitRepository
from infrastructure.rate_limit_config import RateLimitConfig


# Test data
TEST_IP = "192.168.1.100"
TEST_IP_2 = "192.168.1.101"
WHITELISTED_IP = "10.0.0.1"


@pytest.fixture
def redis_client():
    """Fixture to provide Redis client instance."""
    init_redis()
    client = get_redis_client()
    
    yield client
    
    # Cleanup: flush test keys
    for key in client.scan_iter(match="ratelimit:*"):
        client.delete(key)


@pytest.fixture
def repository(redis_client):
    """Fixture to provide RedisRateLimitRepository instance."""
    return RedisRateLimitRepository(redis_client, timeout=1)


@pytest.fixture
def rate_limit_manager(repository):
    """Fixture to provide RateLimitManager instance."""
    return RateLimitManager(repository)


@pytest.fixture
def production_config():
    """Fixture to provide production configuration."""
    return RateLimitConfig(
        enabled=True,
        is_production=True,
        video_only_daily=20,
        audio_only_daily=20,
        video_audio_daily=20,
        total_jobs_daily=60,
        endpoint_hourly={'/api/v1/videos/resolutions': 100},
        batch_per_minute=10,
        whitelist=[WHITELISTED_IP]
    )


@pytest.fixture
def development_config():
    """Fixture to provide development configuration."""
    return RateLimitConfig(
        enabled=True,
        is_production=False,  # Development mode
        video_only_daily=20,
        audio_only_daily=20,
        video_audio_daily=20,
        total_jobs_daily=60,
        endpoint_hourly={'/api/v1/videos/resolutions': 100},
        batch_per_minute=10,
        whitelist=[]
    )


@pytest.fixture
def disabled_config():
    """Fixture to provide disabled configuration."""
    return RateLimitConfig(
        enabled=False,  # Disabled
        is_production=True,
        video_only_daily=20,
        audio_only_daily=20,
        video_audio_daily=20,
        total_jobs_daily=60,
        endpoint_hourly={'/api/v1/videos/resolutions': 100},
        batch_per_minute=10,
        whitelist=[]
    )


@pytest.fixture
def rate_limit_service(rate_limit_manager, production_config):
    """Fixture to provide RateLimitService instance with production config."""
    return RateLimitService(rate_limit_manager, production_config)


# ============================================================================
# check_download_limits() Tests
# ============================================================================


@pytest.mark.integration
def test_check_download_limits_checks_all_three_limits(rate_limit_service):
    """Test check_download_limits() checks per-minute, per-type, and total limits (Requirement 3.1, 3.2, 3.3, 6.1)."""
    # Check download limits
    entities = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    
    # Should return 3 entities (per-minute, per-type, total)
    assert len(entities) == 3
    
    # Verify limit types
    limit_types = [e.limit_type for e in entities]
    assert 'per_minute' in limit_types
    assert 'daily_video-only' in limit_types
    assert 'daily_total' in limit_types


@pytest.mark.integration
def test_check_download_limits_increments_all_counters(rate_limit_service):
    """Test check_download_limits() increments all three counters (Requirement 3.1, 3.2, 3.3)."""
    # First request
    entities1 = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    
    # Verify all counters are at 1
    for entity in entities1:
        assert entity.current_count == 1
    
    # Second request
    entities2 = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    
    # Verify all counters are at 2
    for entity in entities2:
        assert entity.current_count == 2


@pytest.mark.integration
def test_check_download_limits_per_minute_limit_enforced(rate_limit_service):
    """Test per-minute limit is enforced (Requirement 6.1, 6.3)."""
    # Make requests up to the per-minute limit (10)
    for i in range(10):
        entities = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
        per_minute_entity = next(e for e in entities if e.limit_type == 'per_minute')
        assert per_minute_entity.current_count == i + 1
    
    # Next request should raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError) as exc_info:
        rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    
    # Verify error details
    assert exc_info.value.context['limit_type'] == 'per_minute'
    assert exc_info.value.context['limit'] == 10


@pytest.mark.integration
def test_check_download_limits_per_type_limit_enforced(rate_limit_manager):
    """Test per-video-type daily limit is enforced (Requirement 3.1, 3.2, 3.3)."""
    # Create config with higher per-minute limit to test per-type limit
    config = RateLimitConfig(
        enabled=True,
        is_production=True,
        video_only_daily=20,
        audio_only_daily=20,
        video_audio_daily=20,
        total_jobs_daily=60,
        endpoint_hourly={},
        batch_per_minute=100,  # High enough to not interfere
        whitelist=[]
    )
    service = RateLimitService(rate_limit_manager, config)
    
    # Make requests up to the video-only daily limit (20)
    for i in range(20):
        entities = service.check_download_limits(TEST_IP, 'video-only')
        type_entity = next(e for e in entities if e.limit_type == 'daily_video-only')
        assert type_entity.current_count == i + 1
    
    # Next request should raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError) as exc_info:
        service.check_download_limits(TEST_IP, 'video-only')
    
    # Verify error details
    assert exc_info.value.context['limit_type'] == 'daily_video-only'
    assert exc_info.value.context['limit'] == 20


@pytest.mark.integration
def test_check_download_limits_total_daily_limit_enforced(rate_limit_manager):
    """Test total daily job limit is enforced (Requirement 4.1, 4.2)."""
    # Create config with higher per-minute and per-type limits to test total limit
    config = RateLimitConfig(
        enabled=True,
        is_production=True,
        video_only_daily=100,  # High enough to not interfere
        audio_only_daily=100,
        video_audio_daily=100,
        total_jobs_daily=60,
        endpoint_hourly={},
        batch_per_minute=100,  # High enough to not interfere
        whitelist=[]
    )
    service = RateLimitService(rate_limit_manager, config)
    
    # Make requests up to the total daily limit (60)
    for i in range(60):
        entities = service.check_download_limits(TEST_IP, 'video-only')
        total_entity = next(e for e in entities if e.limit_type == 'daily_total')
        assert total_entity.current_count == i + 1
    
    # Next request should raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError) as exc_info:
        service.check_download_limits(TEST_IP, 'video-only')
    
    # Verify error details
    assert exc_info.value.context['limit_type'] == 'daily_total'
    assert exc_info.value.context['limit'] == 60


@pytest.mark.integration
def test_check_download_limits_video_type_mapping(rate_limit_service):
    """Test video type limit mapping (Requirement 3.1, 3.2, 3.3)."""
    # Test video-only
    entities_video = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    video_entity = next(e for e in entities_video if 'daily_video-only' in e.limit_type)
    assert video_entity.limit == 20
    
    # Test audio-only
    entities_audio = rate_limit_service.check_download_limits(TEST_IP_2, 'audio-only')
    audio_entity = next(e for e in entities_audio if 'daily_audio-only' in e.limit_type)
    assert audio_entity.limit == 20
    
    # Test video-audio
    entities_both = rate_limit_service.check_download_limits(TEST_IP, 'video-audio')
    both_entity = next(e for e in entities_both if 'daily_video-audio' in e.limit_type)
    assert both_entity.limit == 20


@pytest.mark.integration
def test_check_download_limits_different_video_types_independent(rate_limit_service):
    """Test different video types have independent counters (Requirement 3.1, 3.2, 3.3)."""
    # Make 5 video-only requests
    for _ in range(5):
        rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    
    # Make 3 audio-only requests
    for _ in range(3):
        rate_limit_service.check_download_limits(TEST_IP, 'audio-only')
    
    # Check video-only counter
    entities_video = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
    video_entity = next(e for e in entities_video if 'daily_video-only' in e.limit_type)
    assert video_entity.current_count == 6  # 5 + 1
    
    # Check audio-only counter
    entities_audio = rate_limit_service.check_download_limits(TEST_IP, 'audio-only')
    audio_entity = next(e for e in entities_audio if 'daily_audio-only' in e.limit_type)
    assert audio_entity.current_count == 4  # 3 + 1
    
    # Check total counter (should be sum of all types)
    total_entity = next(e for e in entities_audio if e.limit_type == 'daily_total')
    assert total_entity.current_count == 10  # 6 + 4


@pytest.mark.integration
def test_check_download_limits_returns_empty_in_development(rate_limit_manager, development_config):
    """Test check_download_limits() returns empty list in development (Requirement 1.1, 1.2)."""
    service = RateLimitService(rate_limit_manager, development_config)
    
    # Check download limits in development mode
    entities = service.check_download_limits(TEST_IP, 'video-only')
    
    # Should return empty list (no enforcement)
    assert entities == []


@pytest.mark.integration
def test_check_download_limits_returns_empty_when_disabled(rate_limit_manager, disabled_config):
    """Test check_download_limits() returns empty list when disabled (Requirement 1.1)."""
    service = RateLimitService(rate_limit_manager, disabled_config)
    
    # Check download limits when disabled
    entities = service.check_download_limits(TEST_IP, 'video-only')
    
    # Should return empty list (no enforcement)
    assert entities == []


# ============================================================================
# check_endpoint_limit() Tests
# ============================================================================


@pytest.mark.integration
def test_check_endpoint_limit_for_configured_endpoint(rate_limit_service):
    """Test check_endpoint_limit() for endpoint with configured limit (Requirement 5.1, 5.3)."""
    endpoint = '/api/v1/videos/resolutions'
    
    # Check endpoint limit
    entity = rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
    
    # Should return entity with correct limit
    assert entity is not None
    assert entity.limit == 100
    assert entity.limit_type == f'endpoint_hourly:{endpoint}'
    assert entity.current_count == 1


@pytest.mark.integration
def test_check_endpoint_limit_increments_counter(rate_limit_service):
    """Test check_endpoint_limit() increments counter (Requirement 5.1, 5.3)."""
    endpoint = '/api/v1/videos/resolutions'
    
    # First request
    entity1 = rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
    assert entity1.current_count == 1
    
    # Second request
    entity2 = rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
    assert entity2.current_count == 2
    
    # Third request
    entity3 = rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
    assert entity3.current_count == 3


@pytest.mark.integration
def test_check_endpoint_limit_enforces_limit(rate_limit_service):
    """Test check_endpoint_limit() enforces hourly limit (Requirement 5.1, 5.3, 5.4)."""
    endpoint = '/api/v1/videos/resolutions'
    
    # Make requests up to the limit (100)
    for i in range(100):
        entity = rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
        assert entity.current_count == i + 1
    
    # Next request should raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError) as exc_info:
        rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
    
    # Verify error details
    assert exc_info.value.context['limit_type'] == f'endpoint_hourly:{endpoint}'
    assert exc_info.value.context['limit'] == 100


@pytest.mark.integration
def test_check_endpoint_limit_returns_none_for_unconfigured_endpoint(rate_limit_service):
    """Test check_endpoint_limit() returns None for endpoint without limit (Requirement 5.1)."""
    endpoint = '/api/v1/downloads/'
    
    # Check endpoint limit for unconfigured endpoint
    entity = rate_limit_service.check_endpoint_limit(TEST_IP, endpoint)
    
    # Should return None
    assert entity is None


@pytest.mark.integration
def test_check_endpoint_limit_returns_none_in_development(rate_limit_manager, development_config):
    """Test check_endpoint_limit() returns None in development (Requirement 1.1, 1.2)."""
    service = RateLimitService(rate_limit_manager, development_config)
    endpoint = '/api/v1/videos/resolutions'
    
    # Check endpoint limit in development mode
    entity = service.check_endpoint_limit(TEST_IP, endpoint)
    
    # Should return None (no enforcement)
    assert entity is None


@pytest.mark.integration
def test_check_endpoint_limit_returns_none_when_disabled(rate_limit_manager, disabled_config):
    """Test check_endpoint_limit() returns None when disabled (Requirement 1.1)."""
    service = RateLimitService(rate_limit_manager, disabled_config)
    endpoint = '/api/v1/videos/resolutions'
    
    # Check endpoint limit when disabled
    entity = service.check_endpoint_limit(TEST_IP, endpoint)
    
    # Should return None (no enforcement)
    assert entity is None


# ============================================================================
# get_most_restrictive_entity() Tests
# ============================================================================


@pytest.mark.integration
def test_get_most_restrictive_entity_returns_lowest_remaining(rate_limit_service):
    """Test get_most_restrictive_entity() returns entity with lowest remaining (Requirement 6.3, 6.4)."""
    # Create entities with different remaining counts
    from domain.rate_limiting.entities import RateLimitEntity
    from datetime import datetime, timedelta
    
    client_ip = ClientIP(TEST_IP)
    reset_at = datetime.utcnow() + timedelta(hours=1)
    
    entity1 = RateLimitEntity(
        client_ip=client_ip,
        limit_type='per_minute',
        current_count=5,
        limit=10,
        reset_at=reset_at
    )  # 5 remaining
    
    entity2 = RateLimitEntity(
        client_ip=client_ip,
        limit_type='daily_video-only',
        current_count=18,
        limit=20,
        reset_at=reset_at
    )  # 2 remaining (most restrictive)
    
    entity3 = RateLimitEntity(
        client_ip=client_ip,
        limit_type='daily_total',
        current_count=50,
        limit=60,
        reset_at=reset_at
    )  # 10 remaining
    
    # Get most restrictive
    most_restrictive = rate_limit_service.get_most_restrictive_entity([entity1, entity2, entity3])
    
    # Should return entity2 (lowest remaining)
    assert most_restrictive == entity2
    assert most_restrictive.remaining() == 2


@pytest.mark.integration
def test_get_most_restrictive_entity_with_single_entity(rate_limit_service):
    """Test get_most_restrictive_entity() with single entity."""
    from domain.rate_limiting.entities import RateLimitEntity
    from datetime import datetime, timedelta
    
    client_ip = ClientIP(TEST_IP)
    reset_at = datetime.utcnow() + timedelta(hours=1)
    
    entity = RateLimitEntity(
        client_ip=client_ip,
        limit_type='per_minute',
        current_count=5,
        limit=10,
        reset_at=reset_at
    )
    
    # Get most restrictive with single entity
    most_restrictive = rate_limit_service.get_most_restrictive_entity([entity])
    
    # Should return the only entity
    assert most_restrictive == entity


@pytest.mark.integration
def test_get_most_restrictive_entity_raises_on_empty_list(rate_limit_service):
    """Test get_most_restrictive_entity() raises ValueError on empty list."""
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        rate_limit_service.get_most_restrictive_entity([])
    
    assert "No entities provided" in str(exc_info.value)


@pytest.mark.integration
def test_get_most_restrictive_entity_with_zero_remaining(rate_limit_service):
    """Test get_most_restrictive_entity() handles zero remaining correctly."""
    from domain.rate_limiting.entities import RateLimitEntity
    from datetime import datetime, timedelta
    
    client_ip = ClientIP(TEST_IP)
    reset_at = datetime.utcnow() + timedelta(hours=1)
    
    entity1 = RateLimitEntity(
        client_ip=client_ip,
        limit_type='per_minute',
        current_count=10,
        limit=10,
        reset_at=reset_at
    )  # 0 remaining (most restrictive)
    
    entity2 = RateLimitEntity(
        client_ip=client_ip,
        limit_type='daily_video-only',
        current_count=15,
        limit=20,
        reset_at=reset_at
    )  # 5 remaining
    
    # Get most restrictive
    most_restrictive = rate_limit_service.get_most_restrictive_entity([entity1, entity2])
    
    # Should return entity1 (zero remaining)
    assert most_restrictive == entity1
    assert most_restrictive.remaining() == 0


# ============================================================================
# Production-Only Enforcement Tests
# ============================================================================


@pytest.mark.integration
def test_production_only_enforcement_enabled_in_production(rate_limit_manager, production_config):
    """Test rate limiting is enforced in production (Requirement 1.1, 1.2)."""
    service = RateLimitService(rate_limit_manager, production_config)
    
    # Verify enforcement is enabled
    assert production_config.should_enforce() is True
    
    # Make requests and verify counters are incremented
    entities = service.check_download_limits(TEST_IP, 'video-only')
    assert len(entities) == 3
    assert all(e.current_count > 0 for e in entities)


@pytest.mark.integration
def test_production_only_enforcement_bypassed_in_development(rate_limit_manager, development_config):
    """Test rate limiting is bypassed in development (Requirement 1.1, 1.2)."""
    service = RateLimitService(rate_limit_manager, development_config)
    
    # Verify enforcement is disabled
    assert development_config.should_enforce() is False
    
    # Make many requests (should not raise error)
    for _ in range(100):
        entities = service.check_download_limits(TEST_IP, 'video-only')
        assert entities == []


@pytest.mark.integration
def test_production_only_enforcement_bypassed_when_disabled(rate_limit_manager, disabled_config):
    """Test rate limiting is bypassed when disabled (Requirement 1.1)."""
    service = RateLimitService(rate_limit_manager, disabled_config)
    
    # Verify enforcement is disabled
    assert disabled_config.should_enforce() is False
    
    # Make many requests (should not raise error)
    for _ in range(100):
        entities = service.check_download_limits(TEST_IP, 'video-only')
        assert entities == []


@pytest.mark.integration
def test_production_only_enforcement_with_environment_variables():
    """Test production-only enforcement respects environment variables (Requirement 1.1, 1.2)."""
    # Test with production environment
    with patch.dict(os.environ, {'FLASK_ENV': 'production', 'RATE_LIMIT_ENABLED': 'true'}):
        config = RateLimitConfig.from_env()
        assert config.should_enforce() is True
    
    # Test with development environment
    with patch.dict(os.environ, {'FLASK_ENV': 'development', 'RATE_LIMIT_ENABLED': 'true'}):
        config = RateLimitConfig.from_env()
        assert config.should_enforce() is False
    
    # Test with disabled flag
    with patch.dict(os.environ, {'FLASK_ENV': 'production', 'RATE_LIMIT_ENABLED': 'false'}):
        config = RateLimitConfig.from_env()
        assert config.should_enforce() is False


# ============================================================================
# Integration Tests with Real Scenarios
# ============================================================================


@pytest.mark.integration
def test_realistic_download_flow(rate_limit_service):
    """Test realistic download flow with multiple limit checks."""
    # User makes 5 video-only downloads
    for i in range(5):
        entities = rate_limit_service.check_download_limits(TEST_IP, 'video-only')
        
        # Verify all counters increment
        per_minute = next(e for e in entities if e.limit_type == 'per_minute')
        per_type = next(e for e in entities if 'daily_video-only' in e.limit_type)
        total = next(e for e in entities if e.limit_type == 'daily_total')
        
        assert per_minute.current_count == i + 1
        assert per_type.current_count == i + 1
        assert total.current_count == i + 1
    
    # User switches to audio-only downloads
    for i in range(3):
        entities = rate_limit_service.check_download_limits(TEST_IP, 'audio-only')
        
        # Verify per-type counter is independent
        per_type = next(e for e in entities if 'daily_audio-only' in e.limit_type)
        assert per_type.current_count == i + 1
        
        # Verify total counter continues incrementing
        total = next(e for e in entities if e.limit_type == 'daily_total')
        assert total.current_count == 5 + i + 1


@pytest.mark.integration
def test_multiple_users_independent_limits(rate_limit_manager):
    """Test multiple users have independent rate limits."""
    # Create config with higher per-minute limit
    config = RateLimitConfig(
        enabled=True,
        is_production=True,
        video_only_daily=20,
        audio_only_daily=20,
        video_audio_daily=20,
        total_jobs_daily=60,
        endpoint_hourly={},
        batch_per_minute=100,  # High enough to not interfere
        whitelist=[]
    )
    service = RateLimitService(rate_limit_manager, config)
    
    # User 1 makes 10 requests
    for _ in range(10):
        service.check_download_limits(TEST_IP, 'video-only')
    
    # User 2 makes 5 requests
    for _ in range(5):
        service.check_download_limits(TEST_IP_2, 'video-only')
    
    # Verify User 1 counter
    entities1 = service.check_download_limits(TEST_IP, 'video-only')
    total1 = next(e for e in entities1 if e.limit_type == 'daily_total')
    assert total1.current_count == 11
    
    # Verify User 2 counter
    entities2 = service.check_download_limits(TEST_IP_2, 'video-only')
    total2 = next(e for e in entities2 if e.limit_type == 'daily_total')
    assert total2.current_count == 6


@pytest.mark.integration
def test_whitelisted_ip_bypasses_all_limits(rate_limit_service):
    """Test whitelisted IP bypasses all rate limits."""
    # Make many requests from whitelisted IP (should not raise error)
    for i in range(150):  # Well over all limits
        entities = rate_limit_service.check_download_limits(WHITELISTED_IP, 'video-only')
        
        # Should not raise error even though counters increment
        # Whitelisted IPs bypass the limit check but counters still increment
        assert len(entities) == 3
        
        # Verify no exception is raised (this is the key test)
        # The fact that we can make 150 requests proves whitelist works
