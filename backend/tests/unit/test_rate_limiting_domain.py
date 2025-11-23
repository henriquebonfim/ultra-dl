"""
Unit tests for rate limiting domain layer.

Tests value objects, entities, and domain services in isolation
with zero external dependencies.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from domain.rate_limiting.value_objects import ClientIP, RateLimit
from domain.rate_limiting.entities import RateLimitEntity
from domain.rate_limiting.services import RateLimitManager
from domain.rate_limiting.repositories import IRateLimitRepository
from domain.errors import RateLimitExceededError


# ============================================================================
# ClientIP Value Object Tests
# ============================================================================

class TestClientIPValueObject:
    """Test ClientIP value object validation and behavior."""
    
    def test_valid_ipv4_address(self):
        """Test valid IPv4 addresses are accepted."""
        valid_ipv4 = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "127.0.0.1",
            "255.255.255.255",
            "0.0.0.0"
        ]
        
        for ip_str in valid_ipv4:
            client_ip = ClientIP(ip_str)
            assert client_ip.address == ip_str
    
    def test_valid_ipv6_address(self):
        """Test valid IPv6 addresses are accepted."""
        valid_ipv6 = [
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:db8:85a3::8a2e:370:7334",
            "::1",
            "fe80::1",
            "::",
            "2001:db8::1"
        ]
        
        for ip_str in valid_ipv6:
            client_ip = ClientIP(ip_str)
            assert client_ip.address == ip_str
    
    def test_invalid_ip_address_raises_value_error(self):
        """Test invalid IP addresses raise ValueError."""
        invalid_ips = [
            "256.1.1.1",           # Invalid IPv4 octet
            "192.168.1",           # Incomplete IPv4
            "192.168.1.1.1",       # Too many octets
            "not-an-ip",           # Not an IP
            "",                    # Empty string
            "192.168.1.1/24",      # CIDR notation
            "gggg::1",             # Invalid IPv6
        ]
        
        for ip_str in invalid_ips:
            with pytest.raises(ValueError, match="Invalid IP address format"):
                ClientIP(ip_str)
    
    def test_is_whitelisted_returns_true_for_whitelisted_ip(self):
        """Test is_whitelisted returns True for IPs in whitelist."""
        client_ip = ClientIP("192.168.1.1")
        whitelist = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        
        assert client_ip.is_whitelisted(whitelist) is True
    
    def test_is_whitelisted_returns_false_for_non_whitelisted_ip(self):
        """Test is_whitelisted returns False for IPs not in whitelist."""
        client_ip = ClientIP("192.168.1.100")
        whitelist = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        
        assert client_ip.is_whitelisted(whitelist) is False
    
    def test_is_whitelisted_with_empty_whitelist(self):
        """Test is_whitelisted returns False with empty whitelist."""
        client_ip = ClientIP("192.168.1.1")
        whitelist = []
        
        assert client_ip.is_whitelisted(whitelist) is False
    
    def test_hash_for_key_generates_16_char_hash(self):
        """Test hash_for_key generates 16-character hexadecimal hash."""
        client_ip = ClientIP("192.168.1.1")
        hash_value = client_ip.hash_for_key()
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_hash_for_key_is_consistent(self):
        """Test hash_for_key returns same hash for same IP."""
        ip_str = "192.168.1.1"
        client_ip1 = ClientIP(ip_str)
        client_ip2 = ClientIP(ip_str)
        
        assert client_ip1.hash_for_key() == client_ip2.hash_for_key()
    
    def test_hash_for_key_is_unique_per_ip(self):
        """Test hash_for_key returns different hashes for different IPs."""
        client_ip1 = ClientIP("192.168.1.1")
        client_ip2 = ClientIP("192.168.1.2")
        
        assert client_ip1.hash_for_key() != client_ip2.hash_for_key()
    
    def test_client_ip_is_immutable(self):
        """Test ClientIP is immutable (frozen dataclass)."""
        client_ip = ClientIP("192.168.1.1")
        
        with pytest.raises(AttributeError):
            client_ip.address = "10.0.0.1"


# ============================================================================
# RateLimit Value Object Tests
# ============================================================================

class TestRateLimitValueObject:
    """Test RateLimit value object validation and behavior."""
    
    def test_valid_rate_limit_creation(self):
        """Test valid rate limit configurations are accepted."""
        rate_limit = RateLimit(
            limit=100,
            window_seconds=3600,
            limit_type="hourly"
        )
        
        assert rate_limit.limit == 100
        assert rate_limit.window_seconds == 3600
        assert rate_limit.limit_type == "hourly"
    
    def test_zero_limit_raises_value_error(self):
        """Test zero limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            RateLimit(limit=0, window_seconds=3600, limit_type="hourly")
    
    def test_negative_limit_raises_value_error(self):
        """Test negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            RateLimit(limit=-10, window_seconds=3600, limit_type="hourly")
    
    def test_zero_window_raises_value_error(self):
        """Test zero window raises ValueError."""
        with pytest.raises(ValueError, match="Window must be positive"):
            RateLimit(limit=100, window_seconds=0, limit_type="hourly")
    
    def test_negative_window_raises_value_error(self):
        """Test negative window raises ValueError."""
        with pytest.raises(ValueError, match="Window must be positive"):
            RateLimit(limit=100, window_seconds=-60, limit_type="hourly")
    
    def test_empty_limit_type_raises_value_error(self):
        """Test empty limit type raises ValueError."""
        with pytest.raises(ValueError, match="Limit type is required"):
            RateLimit(limit=100, window_seconds=3600, limit_type="")
    
    def test_rate_limit_is_immutable(self):
        """Test RateLimit is immutable (frozen dataclass)."""
        rate_limit = RateLimit(limit=100, window_seconds=3600, limit_type="hourly")
        
        with pytest.raises(AttributeError):
            rate_limit.limit = 200
    
    def test_daily_rate_limit(self):
        """Test daily rate limit configuration."""
        rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily")
        
        assert rate_limit.limit == 20
        assert rate_limit.window_seconds == 86400
        assert rate_limit.limit_type == "daily"
    
    def test_per_minute_rate_limit(self):
        """Test per-minute rate limit configuration."""
        rate_limit = RateLimit(limit=10, window_seconds=60, limit_type="per_minute")
        
        assert rate_limit.limit == 10
        assert rate_limit.window_seconds == 60
        assert rate_limit.limit_type == "per_minute"


# ============================================================================
# RateLimitEntity Tests
# ============================================================================

class TestRateLimitEntity:
    """Test RateLimitEntity behavior and methods."""
    
    def test_is_exceeded_returns_false_when_under_limit(self):
        """Test is_exceeded returns False when count is under limit."""
        client_ip = ClientIP("192.168.1.1")
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=5,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert entity.is_exceeded() is False
    
    def test_is_exceeded_returns_true_when_at_limit(self):
        """Test is_exceeded returns True when count equals limit."""
        client_ip = ClientIP("192.168.1.1")
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=10,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert entity.is_exceeded() is True
    
    def test_is_exceeded_returns_true_when_over_limit(self):
        """Test is_exceeded returns True when count exceeds limit."""
        client_ip = ClientIP("192.168.1.1")
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=15,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert entity.is_exceeded() is True
    
    def test_remaining_returns_correct_count(self):
        """Test remaining returns correct number of remaining requests."""
        client_ip = ClientIP("192.168.1.1")
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=7,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert entity.remaining() == 3
    
    def test_remaining_returns_zero_when_at_limit(self):
        """Test remaining returns 0 when at limit."""
        client_ip = ClientIP("192.168.1.1")
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=10,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert entity.remaining() == 0
    
    def test_remaining_returns_zero_when_over_limit(self):
        """Test remaining returns 0 when over limit (not negative)."""
        client_ip = ClientIP("192.168.1.1")
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=15,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert entity.remaining() == 0
    
    def test_to_headers_returns_correct_format(self):
        """Test to_headers returns correctly formatted HTTP headers."""
        client_ip = ClientIP("192.168.1.1")
        reset_time = datetime(2024, 11, 14, 0, 0, 0)
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=7,
            limit=10,
            reset_at=reset_time
        )
        
        headers = entity.to_headers()
        
        assert headers['X-RateLimit-Limit'] == '10'
        assert headers['X-RateLimit-Remaining'] == '3'
        assert headers['X-RateLimit-Reset'] == str(int(reset_time.timestamp()))
    
    def test_to_headers_with_zero_remaining(self):
        """Test to_headers with zero remaining requests."""
        client_ip = ClientIP("192.168.1.1")
        reset_time = datetime(2024, 11, 14, 0, 0, 0)
        entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="daily",
            current_count=10,
            limit=10,
            reset_at=reset_time
        )
        
        headers = entity.to_headers()
        
        assert headers['X-RateLimit-Remaining'] == '0'


# ============================================================================
# RateLimitManager Tests
# ============================================================================

class TestRateLimitManager:
    """Test RateLimitManager domain service."""
    
    def test_check_limit_bypasses_whitelisted_ip(self):
        """Test check_limit bypasses rate limiting for whitelisted IPs."""
        # Setup
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        client_ip = ClientIP("192.168.1.1")
        rate_limit = RateLimit(limit=10, window_seconds=3600, limit_type="hourly")
        whitelist = ["192.168.1.1"]
        
        # Execute
        entity = manager.check_limit(client_ip, rate_limit, whitelist)
        
        # Verify
        assert entity.current_count == 0
        assert entity.limit == rate_limit.limit
        assert not entity.is_exceeded()
        # Repository should not be called for whitelisted IPs
        mock_repo.get_limit_state.assert_not_called()
    
    def test_check_limit_returns_entity_when_under_limit(self):
        """Test check_limit returns entity when under limit."""
        # Setup
        mock_repo = Mock(spec=IRateLimitRepository)
        client_ip = ClientIP("192.168.1.1")
        rate_limit = RateLimit(limit=10, window_seconds=3600, limit_type="hourly")
        
        expected_entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="hourly",
            current_count=5,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        mock_repo.get_limit_state.return_value = expected_entity
        
        manager = RateLimitManager(mock_repo)
        
        # Execute
        entity = manager.check_limit(client_ip, rate_limit, [])
        
        # Verify
        assert entity == expected_entity
        assert not entity.is_exceeded()
        mock_repo.get_limit_state.assert_called_once_with(client_ip, rate_limit)
    
    def test_check_limit_raises_error_when_limit_exceeded(self):
        """Test check_limit raises RateLimitExceededError when limit exceeded."""
        # Setup
        mock_repo = Mock(spec=IRateLimitRepository)
        client_ip = ClientIP("192.168.1.1")
        rate_limit = RateLimit(limit=10, window_seconds=3600, limit_type="hourly")
        
        exceeded_entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="hourly",
            current_count=10,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        mock_repo.get_limit_state.return_value = exceeded_entity
        
        manager = RateLimitManager(mock_repo)
        
        # Execute & Verify
        with pytest.raises(RateLimitExceededError) as exc_info:
            manager.check_limit(client_ip, rate_limit, [])
        
        # Verify error details
        error = exc_info.value
        assert "Rate limit exceeded" in error.technical_message
        assert error.context['limit_type'] == 'hourly'
        assert error.context['limit'] == 10
    
    def test_increment_counter_calls_repository(self):
        """Test increment_counter delegates to repository."""
        # Setup
        mock_repo = Mock(spec=IRateLimitRepository)
        client_ip = ClientIP("192.168.1.1")
        rate_limit = RateLimit(limit=10, window_seconds=3600, limit_type="hourly")
        
        updated_entity = RateLimitEntity(
            client_ip=client_ip,
            limit_type="hourly",
            current_count=6,
            limit=10,
            reset_at=datetime.utcnow() + timedelta(hours=1)
        )
        mock_repo.increment.return_value = updated_entity
        
        manager = RateLimitManager(mock_repo)
        
        # Execute
        entity = manager.increment_counter(client_ip, rate_limit)
        
        # Verify
        assert entity == updated_entity
        mock_repo.increment.assert_called_once_with(client_ip, rate_limit)
    
    def test_calculate_reset_time_for_daily_limit(self):
        """Test calculate_reset_time returns next midnight UTC for daily limits."""
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        rate_limit = RateLimit(limit=20, window_seconds=86400, limit_type="daily")
        current_time = datetime(2024, 11, 13, 15, 30, 45)
        
        reset_time = manager.calculate_reset_time(rate_limit, current_time)
        
        # Should be next midnight UTC
        expected = datetime(2024, 11, 14, 0, 0, 0)
        assert reset_time == expected
    
    def test_calculate_reset_time_for_hourly_limit(self):
        """Test calculate_reset_time returns next hour boundary for hourly limits."""
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        rate_limit = RateLimit(limit=100, window_seconds=3600, limit_type="endpoint_hourly:/api/v1/test")
        current_time = datetime(2024, 11, 13, 15, 30, 45)
        
        reset_time = manager.calculate_reset_time(rate_limit, current_time)
        
        # Should be next hour boundary
        expected = datetime(2024, 11, 13, 16, 0, 0)
        assert reset_time == expected
    
    def test_calculate_reset_time_for_per_minute_limit(self):
        """Test calculate_reset_time returns next minute boundary for per-minute limits."""
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        rate_limit = RateLimit(limit=10, window_seconds=60, limit_type="per_minute")
        current_time = datetime(2024, 11, 13, 15, 30, 45)
        
        reset_time = manager.calculate_reset_time(rate_limit, current_time)
        
        # Should be next minute boundary
        expected = datetime(2024, 11, 13, 15, 31, 0)
        assert reset_time == expected
    
    def test_next_midnight_utc_calculation(self):
        """Test _next_midnight_utc calculates correct midnight boundary."""
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        # Test various times throughout the day
        test_cases = [
            (datetime(2024, 11, 13, 0, 0, 0), datetime(2024, 11, 14, 0, 0, 0)),
            (datetime(2024, 11, 13, 12, 0, 0), datetime(2024, 11, 14, 0, 0, 0)),
            (datetime(2024, 11, 13, 23, 59, 59), datetime(2024, 11, 14, 0, 0, 0)),
            (datetime(2024, 12, 31, 23, 59, 59), datetime(2025, 1, 1, 0, 0, 0)),
        ]
        
        for current, expected in test_cases:
            result = manager._next_midnight_utc(current)
            assert result == expected
    
    def test_next_hour_boundary_calculation(self):
        """Test _next_hour_boundary calculates correct hour boundary."""
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        # Test various times throughout the hour
        test_cases = [
            (datetime(2024, 11, 13, 15, 0, 0), datetime(2024, 11, 13, 16, 0, 0)),
            (datetime(2024, 11, 13, 15, 30, 0), datetime(2024, 11, 13, 16, 0, 0)),
            (datetime(2024, 11, 13, 15, 59, 59), datetime(2024, 11, 13, 16, 0, 0)),
            (datetime(2024, 11, 13, 23, 59, 59), datetime(2024, 11, 14, 0, 0, 0)),
        ]
        
        for current, expected in test_cases:
            result = manager._next_hour_boundary(current)
            assert result == expected
    
    def test_next_minute_boundary_calculation(self):
        """Test _next_minute_boundary calculates correct minute boundary."""
        mock_repo = Mock(spec=IRateLimitRepository)
        manager = RateLimitManager(mock_repo)
        
        # Test various times throughout the minute
        test_cases = [
            (datetime(2024, 11, 13, 15, 30, 0), datetime(2024, 11, 13, 15, 31, 0)),
            (datetime(2024, 11, 13, 15, 30, 30), datetime(2024, 11, 13, 15, 31, 0)),
            (datetime(2024, 11, 13, 15, 30, 59), datetime(2024, 11, 13, 15, 31, 0)),
            (datetime(2024, 11, 13, 15, 59, 59), datetime(2024, 11, 13, 16, 0, 0)),
        ]
        
        for current, expected in test_cases:
            result = manager._next_minute_boundary(current)
            assert result == expected


# ============================================================================
# IRateLimitRepository Interface Tests
# ============================================================================

class TestIRateLimitRepository:
    """Test IRateLimitRepository interface definition."""
    
    def test_interface_has_get_limit_state_method(self):
        """Test interface defines get_limit_state method."""
        assert hasattr(IRateLimitRepository, 'get_limit_state')
        assert callable(getattr(IRateLimitRepository, 'get_limit_state'))
    
    def test_interface_has_increment_method(self):
        """Test interface defines increment method."""
        assert hasattr(IRateLimitRepository, 'increment')
        assert callable(getattr(IRateLimitRepository, 'increment'))
    
    def test_interface_has_reset_counter_method(self):
        """Test interface defines reset_counter method."""
        assert hasattr(IRateLimitRepository, 'reset_counter')
        assert callable(getattr(IRateLimitRepository, 'reset_counter'))
    
    def test_interface_cannot_be_instantiated(self):
        """Test abstract interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IRateLimitRepository()
    
    def test_concrete_implementation_must_implement_all_methods(self):
        """Test concrete implementation must implement all abstract methods."""
        # Create incomplete implementation
        class IncompleteRepo(IRateLimitRepository):
            pass
        
        # Should not be able to instantiate
        with pytest.raises(TypeError):
            IncompleteRepo()
    
    def test_complete_implementation_can_be_instantiated(self):
        """Test complete implementation with all methods can be instantiated."""
        # Create complete implementation
        class CompleteRepo(IRateLimitRepository):
            def get_limit_state(self, client_ip: ClientIP, rate_limit: RateLimit) -> RateLimitEntity:
                return RateLimitEntity(
                    client_ip=client_ip,
                    limit_type=rate_limit.limit_type,
                    current_count=0,
                    limit=rate_limit.limit,
                    reset_at=datetime.utcnow()
                )
            
            def increment(self, client_ip: ClientIP, rate_limit: RateLimit) -> RateLimitEntity:
                return RateLimitEntity(
                    client_ip=client_ip,
                    limit_type=rate_limit.limit_type,
                    current_count=1,
                    limit=rate_limit.limit,
                    reset_at=datetime.utcnow()
                )
            
            def reset_counter(self, client_ip: ClientIP, limit_type: str) -> bool:
                return True
        
        # Should be able to instantiate and use
        repo = CompleteRepo()
        assert isinstance(repo, IRateLimitRepository)
        
        # Test all methods work
        client_ip = ClientIP("192.168.1.1")
        rate_limit = RateLimit(limit=10, window_seconds=3600, limit_type="test")
        
        state = repo.get_limit_state(client_ip, rate_limit)
        assert isinstance(state, RateLimitEntity)
        
        incremented = repo.increment(client_ip, rate_limit)
        assert isinstance(incremented, RateLimitEntity)
        
        reset_result = repo.reset_counter(client_ip, "test")
        assert reset_result is True
    
    def test_get_limit_state_signature(self):
        """Test get_limit_state has correct signature."""
        import inspect
        sig = inspect.signature(IRateLimitRepository.get_limit_state)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'client_ip' in params
        assert 'rate_limit' in params
    
    def test_increment_signature(self):
        """Test increment has correct signature."""
        import inspect
        sig = inspect.signature(IRateLimitRepository.increment)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'client_ip' in params
        assert 'rate_limit' in params
    
    def test_reset_counter_signature(self):
        """Test reset_counter has correct signature."""
        import inspect
        sig = inspect.signature(IRateLimitRepository.reset_counter)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'client_ip' in params
        assert 'limit_type' in params


if __name__ == "__main__":
    """Run tests with pytest."""
    pytest.main([__file__, "-v", "--tb=short"])
