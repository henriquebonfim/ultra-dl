"""
Redis Repository Base Class

Provides atomic operations and distributed locking for job persistence.
Implements the repository pattern for Redis-based data storage.
"""

import json
import time
import uuid
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import redis
from redis.exceptions import LockError, ConnectionError as RedisConnectionError


class RedisRepository:
    """Base Redis repository with atomic operations and distributed locking."""
    
    def __init__(self, redis_client: redis.Redis, key_prefix: str = ""):
        self.redis = redis_client
        self.key_prefix = key_prefix
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed key for Redis storage."""
        return f"{self.key_prefix}:{key}" if self.key_prefix else key
    
    def set_json(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Atomically set JSON data with optional TTL.
        
        Args:
            key: Redis key
            data: Dictionary to store as JSON
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis_key = self._make_key(key)
            json_data = json.dumps(data)
            
            if ttl:
                return self.redis.setex(redis_key, ttl, json_data)
            else:
                return self.redis.set(redis_key, json_data)
        except (RedisConnectionError, TypeError) as e:
            print(f"Error setting JSON data for key {key}: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON data from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Dictionary if found and valid JSON, None otherwise
        """
        try:
            redis_key = self._make_key(key)
            data = self.redis.get(redis_key)
            
            if data is None:
                return None
                
            return json.loads(data.decode('utf-8'))
        except (RedisConnectionError, json.JSONDecodeError) as e:
            print(f"Error getting JSON data for key {key}: {e}")
            return None
    
    def update_json_field(self, key: str, field: str, value: Any) -> bool:
        """
        Atomically update a single field in a JSON object using Lua script.
        
        Args:
            key: Redis key
            field: Field name to update
            value: New value for the field
            
        Returns:
            True if successful, False otherwise
        """
        lua_script = """
        local key = KEYS[1]
        local field = ARGV[1]
        local value = ARGV[2]
        
        local data = redis.call('GET', key)
        if not data then
            return 0
        end
        
        local json_data = cjson.decode(data)
        json_data[field] = cjson.decode(value)
        
        local updated_data = cjson.encode(json_data)
        redis.call('SET', key, updated_data)
        return 1
        """
        
        try:
            redis_key = self._make_key(key)
            json_value = json.dumps(value)
            result = self.redis.eval(lua_script, 1, redis_key, field, json_value)
            return result == 1
        except Exception as e:
            print(f"Error updating JSON field {field} for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            redis_key = self._make_key(key)
            return self.redis.delete(redis_key) > 0
        except RedisConnectionError as e:
            print(f"Error deleting key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            redis_key = self._make_key(key)
            return self.redis.exists(redis_key) > 0
        except RedisConnectionError as e:
            print(f"Error checking existence of key {key}: {e}")
            return False
    
    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Get all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (supports wildcards)
            
        Returns:
            List of matching keys (without prefix)
        """
        try:
            redis_pattern = self._make_key(pattern)
            keys = self.redis.keys(redis_pattern)
            
            # Remove prefix from returned keys
            if self.key_prefix:
                prefix_len = len(self.key_prefix) + 1  # +1 for the colon
                return [key.decode('utf-8')[prefix_len:] for key in keys]
            else:
                return [key.decode('utf-8') for key in keys]
        except RedisConnectionError as e:
            print(f"Error getting keys by pattern {pattern}: {e}")
            return []
    
    @contextmanager
    def distributed_lock(self, lock_name: str, timeout: int = 10, blocking_timeout: int = 5):
        """
        Distributed lock context manager using Redis.
        
        Args:
            lock_name: Name of the lock
            timeout: Lock timeout in seconds
            blocking_timeout: How long to wait for lock acquisition
            
        Yields:
            Lock object if acquired successfully
            
        Raises:
            LockError: If lock cannot be acquired
        """
        lock_key = self._make_key(f"lock:{lock_name}")
        lock = self.redis.lock(lock_key, timeout=timeout, blocking_timeout=blocking_timeout)
        
        try:
            if lock.acquire(blocking=True, blocking_timeout=blocking_timeout):
                yield lock
            else:
                raise LockError(f"Could not acquire lock: {lock_name}")
        finally:
            try:
                lock.release()
            except LockError:
                # Lock may have expired, which is fine
                pass


class RedisConnectionManager:
    """Manages Redis connection with connection pooling."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                 max_connections: int = 20, decode_responses: bool = False):
        self.connection_pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            max_connections=max_connections,
            decode_responses=decode_responses,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance with connection pooling."""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.connection_pool)
        return self._client
    
    def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            return self.client.ping()
        except RedisConnectionError:
            return False
    
    def close(self):
        """Close the connection pool."""
        if self.connection_pool:
            self.connection_pool.disconnect()