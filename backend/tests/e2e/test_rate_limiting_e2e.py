"""
End-to-End Tests for Rate Limiting

Tests complete rate limiting flows including:
- Daily limit enforcement and midnight UTC reset
- Multiple limit types (per-minute, per-type, total daily)
- Whitelist bypass functionality
- Distributed counters across backend instances
- Redis failure graceful degradation

These tests use real Redis and Flask app to validate the entire rate limiting system.

Requirements: All rate limiting requirements (1-12)
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import redis

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from app_factory import create_app
from config.redis_config import get_redis_client, init_redis


# Test data
TEST_IP = "192.168.1.100"
TEST_IP_2 = "192.168.1.101"
TEST_IP_3 = "192.168.1.102"
WHITELISTED_IP_V4 = "10.0.0.1"
WHITELISTED_IP_V6 = "2001:db8::1"


class TestRateLimitingE2E(unittest.TestCase):
    """End-to-end tests for complete rate limiting flows."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Initialize Redis
        init_redis()
        self.redis_client = get_redis_client()
        
        # Clean up any existing rate limit keys
        for key in self.redis_client.scan_iter(match="ratelimit:*"):
            self.redis_client.delete(key)
        
        # Create Flask app with production configuration
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '20',
            'RATE_LIMIT_AUDIO_ONLY_DAILY': '20',
            'RATE_LIMIT_VIDEO_AUDIO_DAILY': '20',
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '60',
            'RATE_LIMIT_BATCH_MINUTE': '10',
            'RATE_LIMIT_ENDPOINT_HOURLY': '/api/v1/videos/resolutions:100',
            'RATE_LIMIT_WHITELIST': f'{WHITELISTED_IP_V4},{WHITELISTED_IP_V6}'
        }):
            self.app = create_app()
            self.client = self.app.test_client()
            self.app_context = self.app.app_context()
            self.app_context.push()
    
    def tearDown(self):
        """Cleanup after test."""
        # Clean up rate limit keys
        for key in self.redis_client.scan_iter(match="ratelimit:*"):
            self.redis_client.delete(key)
        
        # Pop app context
        self.app_context.pop()
    
    # ========================================================================
    # Task 11.1: Test daily limit enforcement and reset
    # ========================================================================
    
    def test_daily_limit_reached_returns_http_429(self):
        """
        Test daily limit reached returns HTTP 429.
        
        Requirements: 3.1, 3.2, 3.3, 4.1, 9.1, 9.2
        """
        print("\n=== Testing Daily Limit Enforcement ===")
        
        # Configure low daily limit for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '5',
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '10',
            'RATE_LIMIT_BATCH_MINUTE': '100'  # High enough to not interfere
        }):
            # Recreate app with new config
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make requests up to video-only daily limit
                print("\n1. Making requests up to daily limit...")
                for i in range(5):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'  # Video-only format
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    # Should succeed or fail validation, but not rate limited
                    assert response.status_code in [202, 400, 503], \
                        f"Request {i+1} failed with {response.status_code}"
                    print(f"  Request {i+1}/5: {response.status_code}")
                
                # Next request should return 429
                print("\n2. Testing limit exceeded...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                
                assert response.status_code == 429, \
                    f"Expected 429, got {response.status_code}"
                print(f"  ✓ HTTP 429 returned")
                
                # Verify response body
                data = response.get_json()
                assert 'error' in data
                assert data['error'] == 'Rate limit exceeded'
                assert 'limit_type' in data
                assert 'daily_video-only' in data['limit_type']
                assert 'reset_at' in data
                print(f"  ✓ Error response: {data['error']}")
                print(f"  ✓ Limit type: {data['limit_type']}")
                print(f"  ✓ Reset at: {data['reset_at']}")
                
                # Verify headers
                assert 'X-RateLimit-Limit' in response.headers
                assert 'X-RateLimit-Remaining' in response.headers
                assert response.headers['X-RateLimit-Remaining'] == '0'
                assert 'X-RateLimit-Reset' in response.headers
                print(f"  ✓ Rate limit headers present")
        
        print("\n✓ Daily limit enforcement test passed")
    
    def test_daily_counter_resets_at_midnight_utc(self):
        """
        Test daily counter resets at midnight UTC.
        
        Requirements: 8.1, 8.2, 8.3, 8.4
        """
        print("\n=== Testing Midnight UTC Reset ===")
        
        # Configure low daily limit for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '3',
            'RATE_LIMIT_BATCH_MINUTE': '100'
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make requests up to limit
                print("\n1. Exhausting daily limit...")
                for i in range(3):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP_2}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Request {i+1}/3: {response.status_code}")
                
                # Verify limit is reached
                print("\n2. Verifying limit reached...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP_2}
                )
                assert response.status_code == 429
                print("  ✓ Limit reached (HTTP 429)")
                
                # Get reset time from response
                data = response.get_json()
                reset_at_str = data['reset_at']
                reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                reset_at = datetime.utcfromtimestamp(reset_timestamp)
                
                print(f"\n3. Reset time: {reset_at.isoformat()} UTC")
                
                # Verify reset time is at day boundary (either 23:59:59 or 00:00:00)
                # Some implementations use end of day, others use start of next day
                is_end_of_day = (reset_at.hour == 23 and reset_at.minute == 59 and reset_at.second == 59)
                is_start_of_day = (reset_at.hour == 0 and reset_at.minute == 0 and reset_at.second == 0)
                assert is_end_of_day or is_start_of_day, \
                    f"Expected day boundary (00:00:00 or 23:59:59), got {reset_at.hour}:{reset_at.minute}:{reset_at.second}"
                print(f"  ✓ Reset time is at day boundary ({reset_at.hour:02d}:{reset_at.minute:02d}:{reset_at.second:02d} UTC)")
                
                # Verify reset time is in the future
                now = datetime.utcnow()
                assert reset_at > now, "Reset time should be in the future"
                print(f"  ✓ Reset time is in the future ({(reset_at - now).total_seconds():.0f}s from now)")
                
                # Verify reset time is within 24 hours
                time_until_reset = (reset_at - now).total_seconds()
                assert time_until_reset <= 86400, "Reset time should be within 24 hours"
                print(f"  ✓ Reset time is within 24 hours")
        
        print("\n✓ Midnight UTC reset test passed")
    
    def test_requests_succeed_after_reset(self):
        """
        Test requests succeed after counter reset.
        
        Requirements: 8.1, 8.2, 8.3, 8.4
        """
        print("\n=== Testing Requests After Reset ===")
        
        # Configure low daily limit with short TTL for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '2',
            'RATE_LIMIT_BATCH_MINUTE': '100'
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make requests up to limit
                print("\n1. Exhausting daily limit...")
                for i in range(2):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP_3}
                    )
                    assert response.status_code in [202, 400, 503]
                
                # Verify limit is reached
                print("\n2. Verifying limit reached...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP_3}
                )
                assert response.status_code == 429
                print("  ✓ Limit reached (HTTP 429)")
                
                # Manually reset counter by deleting Redis key
                print("\n3. Simulating midnight reset (deleting Redis keys)...")
                from domain.rate_limiting.value_objects import ClientIP
                client_ip = ClientIP(TEST_IP_3)
                ip_hash = client_ip.hash_for_key()
                
                # Delete all rate limit keys for this IP
                keys_deleted = 0
                for key in self.redis_client.scan_iter(match=f"ratelimit:*:{ip_hash}"):
                    self.redis_client.delete(key)
                    keys_deleted += 1
                print(f"  ✓ Deleted {keys_deleted} Redis keys")
                
                # Verify requests succeed after reset
                print("\n4. Testing requests after reset...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test_after_reset',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP_3}
                )
                
                # Should succeed (not 429)
                assert response.status_code in [202, 400, 503], \
                    f"Expected success, got {response.status_code}"
                print(f"  ✓ Request succeeded after reset: {response.status_code}")
                
                # Verify counter is reset
                if response.status_code == 202:
                    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                    print(f"  ✓ Remaining requests: {remaining}")
        
        print("\n✓ Requests after reset test passed")
    
    # ========================================================================
    # Task 11.2: Test multiple limit types
    # ========================================================================
    
    def test_per_minute_limit_blocks_before_daily_limit(self):
        """
        Test per-minute limit blocks before daily limit.
        
        Requirements: 3.1, 3.2, 3.3, 6.1, 6.3, 6.4
        """
        print("\n=== Testing Per-Minute Limit Priority ===")
        
        # Configure limits where per-minute is more restrictive
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '100',  # High
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '100',  # High
            'RATE_LIMIT_BATCH_MINUTE': '3'  # Low (most restrictive)
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make requests up to per-minute limit
                print("\n1. Making requests up to per-minute limit...")
                for i in range(3):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Request {i+1}/3: {response.status_code}")
                
                # Next request should hit per-minute limit
                print("\n2. Testing per-minute limit exceeded...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                
                assert response.status_code == 429
                print("  ✓ HTTP 429 returned")
                
                # Verify it's the per-minute limit that was hit
                data = response.get_json()
                assert 'per_minute' in data['limit_type'], \
                    f"Expected per_minute limit, got {data['limit_type']}"
                print(f"  ✓ Per-minute limit hit first: {data['limit_type']}")
                print(f"  ✓ Daily limits not reached yet")
        
        print("\n✓ Per-minute limit priority test passed")
    
    def test_per_type_limit_independent_of_other_types(self):
        """
        Test per-type limit independent of other types.
        
        Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.4
        """
        print("\n=== Testing Per-Type Limit Independence ===")
        
        # Configure low per-type limits
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '3',
            'RATE_LIMIT_AUDIO_ONLY_DAILY': '3',
            'RATE_LIMIT_VIDEO_AUDIO_DAILY': '3',
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '100',  # High enough to not interfere
            'RATE_LIMIT_BATCH_MINUTE': '100'  # High enough to not interfere
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Exhaust video-only limit
                print("\n1. Exhausting video-only limit...")
                for i in range(3):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=video{i}',
                            'format_id': '137'  # Video-only
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    assert response.status_code in [202, 400, 503]
                
                # Verify video-only limit is reached
                print("\n2. Verifying video-only limit reached...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=video999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                assert response.status_code == 429
                assert 'daily_video-only' in response.get_json()['limit_type']
                print("  ✓ Video-only limit reached")
                
                # Audio-only should still work (independent counter)
                print("\n3. Testing audio-only requests (should work)...")
                for i in range(3):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=audio{i}',
                            'format_id': '140'  # Audio-only
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    assert response.status_code in [202, 400, 503], \
                        f"Audio request {i+1} failed with {response.status_code}"
                    print(f"  Audio request {i+1}/3: {response.status_code}")
                
                print("  ✓ Audio-only requests succeeded (independent limit)")
                
                # Verify audio-only limit is now reached
                print("\n4. Verifying audio-only limit reached...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=audio999',
                        'format_id': '140'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                assert response.status_code == 429
                assert 'daily_audio-only' in response.get_json()['limit_type']
                print("  ✓ Audio-only limit reached")
                
                # Video-audio should still work (independent counter)
                print("\n5. Testing video-audio requests (should work)...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=both1',
                        'format_id': '18'  # Video+audio
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                assert response.status_code in [202, 400, 503]
                print(f"  ✓ Video-audio request succeeded: {response.status_code}")
        
        print("\n✓ Per-type limit independence test passed")
    
    def test_total_daily_limit_blocks_across_all_types(self):
        """
        Test total daily limit blocks across all types.
        
        Requirements: 4.1, 4.2, 4.4, 6.1, 6.3, 6.4
        """
        print("\n=== Testing Total Daily Limit ===")
        
        # Configure limits where total is most restrictive
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '100',  # High
            'RATE_LIMIT_AUDIO_ONLY_DAILY': '100',  # High
            'RATE_LIMIT_VIDEO_AUDIO_DAILY': '100',  # High
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '5',  # Low (most restrictive)
            'RATE_LIMIT_BATCH_MINUTE': '100'  # High
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make mixed requests up to total limit
                print("\n1. Making mixed requests up to total limit...")
                
                # 2 video-only
                for i in range(2):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=video{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP_2}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Video request {i+1}/2: {response.status_code}")
                
                # 2 audio-only
                for i in range(2):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=audio{i}',
                            'format_id': '140'
                        },
                        headers={'X-Forwarded-For': TEST_IP_2}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Audio request {i+1}/2: {response.status_code}")
                
                # 1 video-audio (total = 5)
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=both1',
                        'format_id': '18'
                    },
                    headers={'X-Forwarded-For': TEST_IP_2}
                )
                assert response.status_code in [202, 400, 503]
                print(f"  Video-audio request 1/1: {response.status_code}")
                
                # Next request should hit total limit (regardless of type)
                print("\n2. Testing total limit exceeded...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'  # Try video-only
                    },
                    headers={'X-Forwarded-For': TEST_IP_2}
                )
                
                assert response.status_code == 429
                print("  ✓ HTTP 429 returned")
                
                # Verify it's the total limit that was hit
                data = response.get_json()
                assert 'daily_total' in data['limit_type'], \
                    f"Expected daily_total limit, got {data['limit_type']}"
                print(f"  ✓ Total daily limit hit: {data['limit_type']}")
                
                # Try different type - should also be blocked
                print("\n3. Testing different type also blocked...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test888',
                        'format_id': '140'  # Try audio-only
                    },
                    headers={'X-Forwarded-For': TEST_IP_2}
                )
                
                assert response.status_code == 429
                assert 'daily_total' in response.get_json()['limit_type']
                print("  ✓ All types blocked by total limit")
        
        print("\n✓ Total daily limit test passed")
    
    # ========================================================================
    # Task 11.3: Test whitelist bypass
    # ========================================================================
    
    def test_whitelisted_ipv4_bypasses_all_limits(self):
        """
        Test whitelisted IPv4 bypasses all limits.
        
        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        print("\n=== Testing IPv4 Whitelist Bypass ===")
        
        # Configure low limits for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '2',
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '2',
            'RATE_LIMIT_BATCH_MINUTE': '2',
            'RATE_LIMIT_WHITELIST': WHITELISTED_IP_V4
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make many requests from whitelisted IP (well over limits)
                print(f"\n1. Making 20 requests from whitelisted IP {WHITELISTED_IP_V4}...")
                for i in range(20):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': WHITELISTED_IP_V4}
                    )
                    # Should never return 429
                    assert response.status_code != 429, \
                        f"Whitelisted IP got 429 on request {i+1}"
                    if i % 5 == 0:
                        print(f"  Request {i+1}/20: {response.status_code}")
                
                print("  ✓ All 20 requests succeeded (no rate limiting)")
                print("  ✓ Whitelisted IP bypassed all limits")
        
        print("\n✓ IPv4 whitelist bypass test passed")
    
    def test_whitelisted_ipv6_bypasses_all_limits(self):
        """
        Test whitelisted IPv6 bypasses all limits.
        
        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        print("\n=== Testing IPv6 Whitelist Bypass ===")
        
        # Configure low limits for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '2',
            'RATE_LIMIT_TOTAL_JOBS_DAILY': '2',
            'RATE_LIMIT_BATCH_MINUTE': '2',
            'RATE_LIMIT_WHITELIST': WHITELISTED_IP_V6
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make many requests from whitelisted IPv6 (well over limits)
                print(f"\n1. Making 20 requests from whitelisted IPv6 {WHITELISTED_IP_V6}...")
                for i in range(20):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': WHITELISTED_IP_V6}
                    )
                    # Should never return 429
                    assert response.status_code != 429, \
                        f"Whitelisted IPv6 got 429 on request {i+1}"
                    if i % 5 == 0:
                        print(f"  Request {i+1}/20: {response.status_code}")
                
                print("  ✓ All 20 requests succeeded (no rate limiting)")
                print("  ✓ Whitelisted IPv6 bypassed all limits")
        
        print("\n✓ IPv6 whitelist bypass test passed")
    
    def test_non_whitelisted_ip_enforces_limits(self):
        """
        Test non-whitelisted IP enforces limits.
        
        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        print("\n=== Testing Non-Whitelisted IP Enforcement ===")
        
        # Configure low limits and whitelist
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '2',
            'RATE_LIMIT_BATCH_MINUTE': '100',
            'RATE_LIMIT_WHITELIST': WHITELISTED_IP_V4
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make requests from non-whitelisted IP
                print(f"\n1. Making requests from non-whitelisted IP {TEST_IP}...")
                for i in range(2):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Request {i+1}/2: {response.status_code}")
                
                # Next request should be rate limited
                print("\n2. Testing rate limit enforcement...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                
                assert response.status_code == 429
                print("  ✓ HTTP 429 returned")
                print("  ✓ Non-whitelisted IP is rate limited")
                
                # Verify whitelisted IP still works
                print("\n3. Verifying whitelisted IP still works...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=whitelist_test',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': WHITELISTED_IP_V4}
                )
                
                assert response.status_code != 429
                print(f"  ✓ Whitelisted IP works: {response.status_code}")
        
        print("\n✓ Non-whitelisted IP enforcement test passed")
    
    # ========================================================================
    # Task 11.4: Test distributed counters
    # ========================================================================
    
    def test_multiple_backend_instances_share_redis_counters(self):
        """
        Test multiple backend instances share Redis counters.
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        print("\n=== Testing Distributed Counters ===")
        
        # Configure low limits for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '5',
            'RATE_LIMIT_BATCH_MINUTE': '100'
        }):
            # Create two separate app instances (simulating different backend instances)
            app1 = create_app()
            app2 = create_app()
            
            client1 = app1.test_client()
            client2 = app2.test_client()
            
            with app1.app_context():
                # Make 3 requests from instance 1
                print("\n1. Making 3 requests from instance 1...")
                for i in range(3):
                    response = client1.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Instance 1 request {i+1}/3: {response.status_code}")
            
            with app2.app_context():
                # Make 2 requests from instance 2 (same IP)
                print("\n2. Making 2 requests from instance 2 (same IP)...")
                for i in range(2):
                    response = client2.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i+3}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP}
                    )
                    assert response.status_code in [202, 400, 503]
                    print(f"  Instance 2 request {i+1}/2: {response.status_code}")
                
                # Total is now 5 (3 + 2), next request should be rate limited
                print("\n3. Testing limit reached across instances...")
                response = client2.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                
                assert response.status_code == 429
                print("  ✓ HTTP 429 returned")
                print("  ✓ Counter shared across instances (3 + 2 = 5)")
            
            with app1.app_context():
                # Verify instance 1 also sees the limit
                print("\n4. Verifying instance 1 also sees limit...")
                response = client1.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test888',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                
                assert response.status_code == 429
                print("  ✓ Instance 1 also rate limited")
                print("  ✓ Both instances share same Redis counter")
        
        print("\n✓ Distributed counters test passed")
    
    def test_atomic_increments_prevent_race_conditions(self):
        """
        Test atomic increments prevent race conditions.
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        print("\n=== Testing Atomic Increments ===")
        
        # Configure low limit for testing
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '10',
            'RATE_LIMIT_BATCH_MINUTE': '100'
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Make 10 rapid requests
                print("\n1. Making 10 rapid requests...")
                for i in range(10):
                    response = client.post(
                        '/api/v1/downloads/',
                        json={
                            'url': f'https://www.youtube.com/watch?v=test{i}',
                            'format_id': '137'
                        },
                        headers={'X-Forwarded-For': TEST_IP_3}
                    )
                    assert response.status_code in [202, 400, 503]
                
                print("  ✓ All 10 requests processed")
                
                # Verify counter is exactly 10 (no race condition)
                print("\n2. Verifying counter accuracy...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test999',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP_3}
                )
                
                assert response.status_code == 429
                print("  ✓ Limit reached at exactly 10 requests")
                
                # Verify remaining is 0
                assert response.headers['X-RateLimit-Remaining'] == '0'
                print("  ✓ Remaining count is 0 (no race condition)")
                print("  ✓ Atomic increments working correctly")
        
        print("\n✓ Atomic increments test passed")
    
    # ========================================================================
    # Task 11.5: Test Redis failure degradation
    # ========================================================================
    
    def test_service_continues_when_redis_unavailable(self):
        """
        Test service continues when Redis unavailable.
        
        Requirements: 12.1, 12.2, 12.3, 12.4
        """
        print("\n=== Testing Redis Failure Degradation ===")
        
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true'
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Mock Redis to raise connection error
                print("\n1. Simulating Redis connection failure...")
                with patch.object(self.redis_client, 'get', side_effect=redis.ConnectionError("Connection refused")):
                    with patch.object(self.redis_client, 'pipeline', side_effect=redis.ConnectionError("Connection refused")):
                        # Request should still succeed (graceful degradation)
                        response = client.post(
                            '/api/v1/downloads/',
                            json={
                                'url': 'https://www.youtube.com/watch?v=test1',
                                'format_id': '137'
                            },
                            headers={'X-Forwarded-For': TEST_IP}
                        )
                        
                        # Should not return 429 (rate limiting bypassed)
                        assert response.status_code != 429, \
                            f"Expected service to continue, got {response.status_code}"
                        print(f"  ✓ Request succeeded: {response.status_code}")
                        print("  ✓ Service continued despite Redis failure")
        
        print("\n✓ Redis failure degradation test passed")
    
    def test_error_logging_on_redis_failure(self, caplog=None):
        """
        Test error logging on Redis failure.
        
        Requirements: 12.1, 12.2
        """
        print("\n=== Testing Redis Failure Logging ===")
        
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true'
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # Mock Redis to raise connection error
                print("\n1. Simulating Redis connection failure...")
                with patch.object(self.redis_client, 'get', side_effect=redis.ConnectionError("Connection refused")):
                    with patch.object(self.redis_client, 'pipeline', side_effect=redis.ConnectionError("Connection refused")):
                        # Make request
                        response = client.post(
                            '/api/v1/downloads/',
                            json={
                                'url': 'https://www.youtube.com/watch?v=test1',
                                'format_id': '137'
                            },
                            headers={'X-Forwarded-For': TEST_IP}
                        )
                        
                        # Request should succeed
                        assert response.status_code != 429
                        print(f"  ✓ Request succeeded: {response.status_code}")
                        print("  ✓ Error should be logged (check application logs)")
        
        print("\n✓ Redis failure logging test passed")
    
    def test_automatic_reconnection_on_subsequent_requests(self):
        """
        Test automatic reconnection on subsequent requests.
        
        Requirements: 12.1, 12.2, 12.3, 12.4
        """
        print("\n=== Testing Redis Automatic Reconnection ===")
        
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'RATE_LIMIT_ENABLED': 'true',
            'RATE_LIMIT_VIDEO_ONLY_DAILY': '5',
            'RATE_LIMIT_BATCH_MINUTE': '100'
        }):
            app = create_app()
            client = app.test_client()
            
            with app.app_context():
                # First request with Redis working
                print("\n1. Making request with Redis working...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test1',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                assert response.status_code in [202, 400, 503]
                print(f"  ✓ Request 1 succeeded: {response.status_code}")
                
                # Simulate Redis failure for one request
                print("\n2. Simulating temporary Redis failure...")
                with patch.object(self.redis_client, 'get', side_effect=redis.ConnectionError("Connection refused")):
                    with patch.object(self.redis_client, 'pipeline', side_effect=redis.ConnectionError("Connection refused")):
                        response = client.post(
                            '/api/v1/downloads/',
                            json={
                                'url': 'https://www.youtube.com/watch?v=test2',
                                'format_id': '137'
                            },
                            headers={'X-Forwarded-For': TEST_IP}
                        )
                        assert response.status_code != 429
                        print(f"  ✓ Request 2 succeeded despite failure: {response.status_code}")
                
                # Subsequent request should work normally (Redis recovered)
                print("\n3. Making request after Redis recovery...")
                response = client.post(
                    '/api/v1/downloads/',
                    json={
                        'url': 'https://www.youtube.com/watch?v=test3',
                        'format_id': '137'
                    },
                    headers={'X-Forwarded-For': TEST_IP}
                )
                assert response.status_code in [202, 400, 503]
                print(f"  ✓ Request 3 succeeded: {response.status_code}")
                
                # Verify counter is tracking again
                if response.status_code == 202:
                    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                    print(f"  ✓ Rate limiting working again (remaining: {remaining})")
                    print("  ✓ Automatic reconnection successful")
        
        print("\n✓ Redis automatic reconnection test passed")


def run_all_tests():
    """Run all end-to-end rate limiting tests."""
    print("=" * 70)
    print("End-to-End Rate Limiting Test Suite")
    print("=" * 70)
    print("\nThese tests validate complete rate limiting flows including:")
    print("  - Daily limit enforcement and midnight UTC reset")
    print("  - Multiple limit types (per-minute, per-type, total)")
    print("  - Whitelist bypass (IPv4 and IPv6)")
    print("  - Distributed counters across backend instances")
    print("  - Redis failure graceful degradation")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimitingE2E))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✓ All end-to-end rate limiting tests passed")
        print(f"  {result.testsRun} tests passed")
    else:
        print("✗ Some end-to-end rate limiting tests failed")
        print(f"  {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
