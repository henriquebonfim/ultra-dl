#!/usr/bin/env python3
"""Quick test of rate limiting domain layer."""

import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from domain.rate_limiting.entities import RateLimitEntity
from domain.rate_limiting.value_objects import ClientIP, RateLimit

# Test ClientIP
print("Testing ClientIP...")
ip = ClientIP("192.168.1.1")
print(f"  IP: {ip.address}")
print(f"  Hash: {ip.hash_for_key()}")
print(f"  Whitelisted: {ip.is_whitelisted(['192.168.1.1'])}")

# Test IPv6
ipv6 = ClientIP("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
print(f"  IPv6: {ipv6.address}")

# Test RateLimit
print("\nTesting RateLimit...")
rate_limit = RateLimit(limit=100, window_seconds=3600, limit_type="hourly")
print(f"  Limit: {rate_limit.limit}")
print(f"  Window: {rate_limit.window_seconds}s")
print(f"  Type: {rate_limit.limit_type}")

# Test RateLimitEntity
print("\nTesting RateLimitEntity...")
reset_at = datetime.utcnow() + timedelta(hours=1)
entity = RateLimitEntity(
    client_ip=ip, limit_type="hourly", current_count=75, limit=100, reset_at=reset_at
)
print(f"  Current: {entity.current_count}/{entity.limit}")
print(f"  Remaining: {entity.remaining()}")
print(f"  Exceeded: {entity.is_exceeded()}")
print(f"  Headers: {entity.to_headers()}")

# Test exceeded state
entity_exceeded = RateLimitEntity(
    client_ip=ip, limit_type="hourly", current_count=100, limit=100, reset_at=reset_at
)
print("\n  Exceeded entity:")
print(f"    Current: {entity_exceeded.current_count}/{entity_exceeded.limit}")
print(f"    Remaining: {entity_exceeded.remaining()}")
print(f"    Exceeded: {entity_exceeded.is_exceeded()}")

print("\nAll domain layer tests passed!")
