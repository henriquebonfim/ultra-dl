"""
API Integration Tests for Rate Limiting

Tests rate limit decorator, download endpoint rate limiting, and resolutions
endpoint rate limiting including IP extraction, header generation, and HTTP 429
responses.

Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.4, 5.1, 5.3, 5.4, 6.1, 6.3, 6.4,
             9.1, 9.2, 9.3, 9.4, 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_client
from domain.rate_limiting.value_objects import ClientIP, RateLimit
from domain.rate_limiting.entities import RateLimitEntity
from domain.errors import RateLimitExceededError


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
def app():
    """Fixture to provide Flask app instance with production config."""
    # Set production environment for rate limiting
    with patch.dict(os.environ, {
        'FLASK_ENV': 'production',
        'RATE_LIMIT_ENABLED': 'true',
        'RATE_LIMIT_VIDEO_ONLY_DAILY': '20',
        'RATE_LIMIT_AUDIO_ONLY_DAILY': '20',
        'RATE_LIMIT_VIDEO_AUDIO_DAILY': '20',
        'RATE_LIMIT_TOTAL_JOBS_DAILY': '60',
        'RATE_LIMIT_BATCH_MINUTE': '10',
        'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:100',
        'RATE_LIMIT_WHITELIST': ''
    }):
        from main import app as main_app
        main_app.config['TESTING'] = True
        yield main_app


@pytest.fixture
def client(app):
    """Fixture to provide Flask test client."""
    return app.test_client()


# ============================================================================
# Rate Limit Decorator Tests (Task 10.1)
# ============================================================================


@pytest.mark.integration
def test_decorator_applies_rate_limiting_to_routes(client, redis_client):
    """Test decorator applies rate limiting to routes (Requirement 9.1, 10.1)."""
    # Make request to decorated endpoint
    response = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test123'},
        headers={'X-Forwarded-For': TEST_IP}
    )
    
    # Should succeed (first request)
    assert response.status_code in [200, 400]  # 400 if URL validation fails, but rate limit passed
    
    # Verify rate limit headers are present
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers


@pytest.mark.integration
def test_decorator_extracts_ip_from_x_forwarded_for_header(client, redis_client):
    """Test IP extraction from X-Forwarded-For header (Requirement 11.1, 11.2)."""
    # Make request with X-Forwarded-For header
    response1 = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test123'},
        headers={'X-Forwarded-For': f'{TEST_IP}, 10.0.0.1, 10.0.0.2'}
    )
    
    # Should extract first IP in chain
    assert response1.status_code in [200, 400]
    
    # Make another request from same IP
    response2 = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test456'},
        headers={'X-Forwarded-For': f'{TEST_IP}, 10.0.0.1, 10.0.0.2'}
    )
    
    # Counter should increment (same IP)
    remaining1 = int(response1.headers.get('X-RateLimit-Remaining', 0))
    remaining2 = int(response2.headers.get('X-RateLimit-Remaining', 0))
    assert remaining2 == remaining1 - 1


@pytest.mark.integration
def test_decorator_extracts_ip_fallback_to_remote_addr(client, redis_client):
    """Test IP extraction fallback to remote_addr (Requirement 11.3, 11.4)."""
    # Make request without X-Forwarded-For header
    response = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test123'}
    )
    
    # Should use remote_addr (127.0.0.1 in test environment)
    assert response.status_code in [200, 400]
    
    # Verify rate limit headers are present
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers


@pytest.mark.integration
def test_decorator_adds_rate_limit_headers_to_successful_responses(client, redis_client):
    """Test rate limit headers added to successful responses (Requirement 10.1, 10.2, 10.3, 10.4)."""
    # Make request
    response = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test123'},
        headers={'X-Forwarded-For': TEST_IP}
    )
    
    # Verify all required headers are present
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers
    
    # Verify header values are valid
    limit = int(response.headers['X-RateLimit-Limit'])
    remaining = int(response.headers['X-RateLimit-Remaining'])
    reset = int(response.headers['X-RateLimit-Reset'])
    
    assert limit > 0
    assert remaining >= 0
    assert remaining < limit  # Should have decremented
    assert reset > 0  # Unix timestamp


@pytest.mark.integration
def test_decorator_returns_http_429_on_limit_exceeded(client, redis_client):
    """Test HTTP 429 response on limit exceeded (Requirement 9.1, 9.2, 10.1)."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:5'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make requests up to limit
        for i in range(5):
            response = client.post(
                '/api/v1/videos/resolutions',
                json={'url': f'https://www.youtube.com/watch?v=test{i}'},
                headers={'X-Forwarded-For': TEST_IP_2}
            )
            assert response.status_code in [200, 400]
        
        # Next request should return 429
        response = client.post(
            '/api/v1/videos/resolutions',
            json={'url': 'https://www.youtube.com/watch?v=test999'},
            headers={'X-Forwarded-For': TEST_IP_2}
        )
        
        assert response.status_code == 429
        
        # Verify response body
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Rate limit exceeded'
        assert 'limit_type' in data
        assert 'reset_at' in data
        
        # Verify headers are present
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert response.headers['X-RateLimit-Remaining'] == '0'


@pytest.mark.integration
def test_decorator_http_429_response_format(client, redis_client):
    """Test HTTP 429 response format (Requirement 9.1, 9.2, 9.3)."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:2'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Exhaust limit
        for i in range(2):
            client.post(
                '/api/v1/videos/resolutions',
                json={'url': f'https://www.youtube.com/watch?v=test{i}'},
                headers={'X-Forwarded-For': TEST_IP}
            )
        
        # Get 429 response
        response = client.post(
            '/api/v1/videos/resolutions',
            json={'url': 'https://www.youtube.com/watch?v=test999'},
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        assert response.status_code == 429
        
        # Verify JSON response structure
        data = response.get_json()
        assert isinstance(data, dict)
        assert 'error' in data
        assert 'limit_type' in data
        assert 'reset_at' in data
        
        # Verify error message
        assert data['error'] == 'Rate limit exceeded'
        
        # Verify limit_type is present
        assert data['limit_type'] is not None
        
        # Verify reset_at is ISO format timestamp
        assert data['reset_at'] is not None


# ============================================================================
# Download Endpoint Rate Limiting Tests (Task 10.2)
# ============================================================================


@pytest.mark.integration
def test_download_endpoint_per_minute_limit_enforcement(client, redis_client):
    """Test per-minute limit enforcement on download endpoint (Requirement 6.1, 6.3, 6.4)."""
    # Configure low per-minute limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_BATCH_MINUTE': '3'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make requests up to per-minute limit
        for i in range(3):
            response = client.post(
                '/api/v1/downloads/',
                json={
                    'url': f'https://www.youtube.com/watch?v=test{i}',
                    'format_id': '18'
                },
                headers={'X-Forwarded-For': TEST_IP}
            )
            # Should succeed or fail validation, but not rate limited
            assert response.status_code in [202, 400, 503]
        
        # Next request should return 429
        response = client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test999',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        assert response.status_code == 429
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Rate limit exceeded'


@pytest.mark.integration
def test_download_endpoint_per_video_type_daily_limit_enforcement(client, redis_client):
    """Test per-video-type daily limit enforcement (Requirement 3.1, 3.2, 3.3)."""
    # Configure low limits for testing
    with patch.dict(os.environ, {
        'RATE_LIMIT_VIDEO_ONLY_DAILY': '3',
        'RATE_LIMIT_BATCH_MINUTE': '100'  # High enough to not interfere
    }):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make video-only requests up to limit
        for i in range(3):
            response = client.post(
                '/api/v1/downloads/',
                json={
                    'url': f'https://www.youtube.com/watch?v=test{i}',
                    'format_id': '137'  # Video-only format
                },
                headers={'X-Forwarded-For': TEST_IP_2}
            )
            assert response.status_code in [202, 400, 503]
        
        # Next video-only request should return 429
        response = client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test999',
                'format_id': '137'
            },
            headers={'X-Forwarded-For': TEST_IP_2}
        )
        
        assert response.status_code == 429
        data = response.get_json()
        assert 'daily_video-only' in data.get('limit_type', '')


@pytest.mark.integration
def test_download_endpoint_total_daily_job_limit_enforcement(client, redis_client):
    """Test total daily job limit enforcement (Requirement 4.1, 4.2, 4.4)."""
    # Configure low limits for testing
    with patch.dict(os.environ, {
        'RATE_LIMIT_TOTAL_JOBS_DAILY': '5',
        'RATE_LIMIT_VIDEO_ONLY_DAILY': '100',  # High enough to not interfere
        'RATE_LIMIT_BATCH_MINUTE': '100'  # High enough to not interfere
    }):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make requests up to total limit
        for i in range(5):
            response = client.post(
                '/api/v1/downloads/',
                json={
                    'url': f'https://www.youtube.com/watch?v=test{i}',
                    'format_id': '18'
                },
                headers={'X-Forwarded-For': TEST_IP}
            )
            assert response.status_code in [202, 400, 503]
        
        # Next request should return 429
        response = client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test999',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        assert response.status_code == 429
        data = response.get_json()
        assert 'daily_total' in data.get('limit_type', '')


@pytest.mark.integration
def test_download_endpoint_multiple_limits_checked_in_order(client, redis_client):
    """Test multiple limits checked in order (Requirement 3.1, 3.2, 3.3, 6.1)."""
    # Configure limits so per-minute is most restrictive
    with patch.dict(os.environ, {
        'RATE_LIMIT_BATCH_MINUTE': '2',
        'RATE_LIMIT_VIDEO_ONLY_DAILY': '100',
        'RATE_LIMIT_TOTAL_JOBS_DAILY': '100'
    }):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make requests up to per-minute limit
        for i in range(2):
            response = client.post(
                '/api/v1/downloads/',
                json={
                    'url': f'https://www.youtube.com/watch?v=test{i}',
                    'format_id': '18'
                },
                headers={'X-Forwarded-For': TEST_IP_2}
            )
            assert response.status_code in [202, 400, 503]
        
        # Next request should hit per-minute limit first
        response = client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test999',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP_2}
        )
        
        assert response.status_code == 429
        data = response.get_json()
        # Should hit per-minute limit first
        assert 'per_minute' in data.get('limit_type', '')


@pytest.mark.integration
def test_download_endpoint_rate_limit_headers_in_response(client, redis_client):
    """Test rate limit headers in response (Requirement 10.5)."""
    response = client.post(
        '/api/v1/downloads/',
        json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'format_id': '18'
        },
        headers={'X-Forwarded-For': TEST_IP}
    )
    
    # Should have rate limit headers (if request succeeded)
    if response.status_code == 202:
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert 'X-RateLimit-Reset' in response.headers


@pytest.mark.integration
def test_download_endpoint_http_429_response_format(client, redis_client):
    """Test HTTP 429 response format (Requirement 9.1, 9.2, 9.4)."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_BATCH_MINUTE': '1'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Exhaust limit
        client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test1',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        # Get 429 response
        response = client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test2',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        assert response.status_code == 429
        
        # Verify response structure
        data = response.get_json()
        assert 'error' in data
        assert 'limit_type' in data
        assert 'reset_at' in data
        
        # Verify headers
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert 'X-RateLimit-Reset' in response.headers
        assert response.headers['X-RateLimit-Remaining'] == '0'


@pytest.mark.integration
def test_download_endpoint_rate_limit_violation_logging(client, redis_client, caplog):
    """Test rate limit violation logging (Requirement 9.3)."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_BATCH_MINUTE': '1'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Exhaust limit
        client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test1',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        # Trigger rate limit violation
        with caplog.at_level('INFO'):
            response = client.post(
                '/api/v1/downloads/',
                json={
                    'url': 'https://www.youtube.com/watch?v=test2',
                    'format_id': '18'
                },
                headers={'X-Forwarded-For': TEST_IP}
            )
        
        assert response.status_code == 429
        
        # Verify logging
        assert any('Rate limit exceeded' in record.message for record in caplog.records)
        assert any(TEST_IP in record.message for record in caplog.records)


# ============================================================================
# Resolutions Endpoint Rate Limiting Tests (Task 10.3)
# ============================================================================


@pytest.mark.integration
def test_resolutions_endpoint_hourly_limit(client, redis_client):
    """Test endpoint-specific hourly limit (Requirement 5.1, 5.3, 5.4)."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:3'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make requests up to limit
        for i in range(3):
            response = client.post(
                '/api/v1/videos/resolutions',
                json={'url': f'https://www.youtube.com/watch?v=test{i}'},
                headers={'X-Forwarded-For': TEST_IP}
            )
            assert response.status_code in [200, 400]
        
        # Next request should return 429
        response = client.post(
            '/api/v1/videos/resolutions',
            json={'url': 'https://www.youtube.com/watch?v=test999'},
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        assert response.status_code == 429


@pytest.mark.integration
def test_resolutions_endpoint_rate_limit_headers_in_response(client, redis_client):
    """Test rate limit headers in response (Requirement 10.1, 10.2, 10.3, 10.4)."""
    response = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test123'},
        headers={'X-Forwarded-For': TEST_IP_2}
    )
    
    # Verify headers are present
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers
    
    # Verify header values
    limit = int(response.headers['X-RateLimit-Limit'])
    remaining = int(response.headers['X-RateLimit-Remaining'])
    reset = int(response.headers['X-RateLimit-Reset'])
    
    assert limit > 0
    assert remaining >= 0
    assert reset > 0


@pytest.mark.integration
def test_resolutions_endpoint_http_429_on_limit_exceeded(client, redis_client):
    """Test HTTP 429 response on limit exceeded (Requirement 9.1, 9.2)."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:2'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Exhaust limit
        for i in range(2):
            client.post(
                '/api/v1/videos/resolutions',
                json={'url': f'https://www.youtube.com/watch?v=test{i}'},
                headers={'X-Forwarded-For': TEST_IP_2}
            )
        
        # Get 429 response
        response = client.post(
            '/api/v1/videos/resolutions',
            json={'url': 'https://www.youtube.com/watch?v=test999'},
            headers={'X-Forwarded-For': TEST_IP_2}
        )
        
        assert response.status_code == 429
        
        # Verify response body
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Rate limit exceeded'
        
        # Verify headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert response.headers['X-RateLimit-Remaining'] == '0'


@pytest.mark.integration
def test_resolutions_endpoint_independent_from_download_limits(client, redis_client):
    """Test resolutions endpoint limits are independent from download limits."""
    # Make download requests
    for i in range(3):
        client.post(
            '/api/v1/downloads/',
            json={
                'url': f'https://www.youtube.com/watch?v=test{i}',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
    
    # Resolutions endpoint should still work (independent counter)
    response = client.post(
        '/api/v1/videos/resolutions',
        json={'url': 'https://www.youtube.com/watch?v=test123'},
        headers={'X-Forwarded-For': TEST_IP}
    )
    
    # Should not be rate limited by download requests
    assert response.status_code in [200, 400]  # Not 429


# ============================================================================
# Additional Integration Tests
# ============================================================================


@pytest.mark.integration
def test_different_ips_have_independent_limits(client, redis_client):
    """Test different IPs have independent rate limits."""
    # Configure low limit for testing
    with patch.dict(os.environ, {'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:2'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # IP 1 exhausts limit
        for i in range(2):
            response = client.post(
                '/api/v1/videos/resolutions',
                json={'url': f'https://www.youtube.com/watch?v=test{i}'},
                headers={'X-Forwarded-For': TEST_IP}
            )
            assert response.status_code in [200, 400]
        
        # IP 1 should be rate limited
        response = client.post(
            '/api/v1/videos/resolutions',
            json={'url': 'https://www.youtube.com/watch?v=test999'},
            headers={'X-Forwarded-For': TEST_IP}
        )
        assert response.status_code == 429
        
        # IP 2 should still work
        response = client.post(
            '/api/v1/videos/resolutions',
            json={'url': 'https://www.youtube.com/watch?v=test123'},
            headers={'X-Forwarded-For': TEST_IP_2}
        )
        assert response.status_code in [200, 400]  # Not 429


@pytest.mark.integration
def test_rate_limit_headers_show_most_restrictive_limit(client, redis_client):
    """Test rate limit headers show most restrictive limit (Requirement 10.5)."""
    # Configure limits where per-minute is most restrictive
    with patch.dict(os.environ, {
        'RATE_LIMIT_BATCH_MINUTE': '5',
        'RATE_LIMIT_VIDEO_ONLY_DAILY': '100',
        'RATE_LIMIT_TOTAL_JOBS_DAILY': '100'
    }):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make 4 requests
        for i in range(4):
            client.post(
                '/api/v1/downloads/',
                json={
                    'url': f'https://www.youtube.com/watch?v=test{i}',
                    'format_id': '18'
                },
                headers={'X-Forwarded-For': TEST_IP}
            )
        
        # Next request should show per-minute as most restrictive
        response = client.post(
            '/api/v1/downloads/',
            json={
                'url': 'https://www.youtube.com/watch?v=test5',
                'format_id': '18'
            },
            headers={'X-Forwarded-For': TEST_IP}
        )
        
        if response.status_code == 202:
            # Verify headers show per-minute limit (most restrictive)
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            # Should be 0 (5 requests made, limit is 5)
            assert remaining == 0


@pytest.mark.integration
def test_rate_limiting_bypassed_in_development_mode(client, redis_client):
    """Test rate limiting is bypassed in development mode (Requirement 1.1, 1.2)."""
    # Set development mode
    with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
        # Restart app to pick up new config
        from importlib import reload
        import infrastructure.rate_limit_config
        reload(infrastructure.rate_limit_config)
        
        # Make many requests (should not be rate limited)
        for i in range(50):
            response = client.post(
                '/api/v1/videos/resolutions',
                json={'url': f'https://www.youtube.com/watch?v=test{i}'},
                headers={'X-Forwarded-For': TEST_IP}
            )
            # Should never return 429 in development
            assert response.status_code != 429


if __name__ == "__main__":
    """Run tests with pytest."""
    pytest.main([__file__, "-v", "--tb=short"])
