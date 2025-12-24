"""
Redis Configuration

Configures Redis connection settings and provides factory functions
for creating Redis clients and repositories.
"""

import os
from typing import Optional

from src.infrastructure.redis_repository import RedisConnectionManager, RedisRepository


class RedisConfig:
    """Redis configuration settings."""

    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD")
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))

        # Redis URL format: redis://[:password@]host:port/db
        self.url = os.getenv("REDIS_URL")
        if self.url:
            # Parse Redis URL if provided
            import redis

            connection_params = redis.connection.parse_url(self.url)
            self.host = connection_params.get("host", self.host)
            self.port = connection_params.get("port", self.port)
            self.db = connection_params.get("db", self.db)
            self.password = connection_params.get("password", self.password)


# Global Redis connection manager
_redis_manager: Optional[RedisConnectionManager] = None


def init_redis(config: Optional[RedisConfig] = None) -> RedisConnectionManager:
    """
    Initialize Redis connection manager.

    Args:
        config: Redis configuration, uses default if None

    Returns:
        RedisConnectionManager instance
    """
    global _redis_manager

    if config is None:
        config = RedisConfig()

    connection_kwargs = {
        "host": config.host,
        "port": config.port,
        "db": config.db,
        "max_connections": config.max_connections,
    }

    if config.password:
        connection_kwargs["password"] = config.password

    _redis_manager = RedisConnectionManager(**connection_kwargs)
    return _redis_manager


def get_redis_client():
    """
    Get Redis client instance.

    Returns:
        Redis client

    Raises:
        RuntimeError: If Redis is not initialized
    """
    if _redis_manager is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")

    return _redis_manager.client


def get_redis_repository(key_prefix: str = "") -> RedisRepository:
    """
    Get Redis repository with optional key prefix.

    Args:
        key_prefix: Prefix for all keys in this repository

    Returns:
        RedisRepository instance
    """
    client = get_redis_client()
    return RedisRepository(client, key_prefix)


def redis_health_check() -> bool:
    """
    Check Redis connection health.

    Returns:
        True if Redis is healthy, False otherwise
    """
    if _redis_manager is None:
        return False

    return _redis_manager.health_check()
