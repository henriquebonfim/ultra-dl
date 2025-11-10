"""
Quick test script to verify core infrastructure components.
Run with: python test_infrastructure.py
"""

import os
import sys
import time

# Set up environment for testing (use redis service name in Docker)
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from config.redis_config import init_redis, get_redis_repository, redis_health_check
from infrastructure.redis_repository import RedisRepository


def test_redis_connection():
    """Test Redis connection and health check."""
    print("Testing Redis connection...")
    init_redis()
    
    if redis_health_check():
        print("✓ Redis connection successful")
        return True
    else:
        print("✗ Redis connection failed")
        return False


def test_redis_operations():
    """Test basic Redis operations."""
    print("\nTesting Redis operations...")
    repo = get_redis_repository("test")
    
    # Test set and get
    test_data = {"key": "value", "number": 42}
    repo.set_json("test_key", test_data, ttl=60)
    retrieved = repo.get_json("test_key")
    
    if retrieved == test_data:
        print("✓ Set/Get JSON operations successful")
    else:
        print("✗ Set/Get JSON operations failed")
        return False
    
    # Test update field
    repo.update_json_field("test_key", "number", 100)
    updated = repo.get_json("test_key")
    
    if updated["number"] == 100:
        print("✓ Update JSON field successful")
    else:
        print("✗ Update JSON field failed")
        return False
    
    # Test exists
    if repo.exists("test_key"):
        print("✓ Key exists check successful")
    else:
        print("✗ Key exists check failed")
        return False
    
    # Test delete
    repo.delete("test_key")
    if not repo.exists("test_key"):
        print("✓ Delete operation successful")
    else:
        print("✗ Delete operation failed")
        return False
    
    return True


def test_distributed_locking():
    """Test distributed locking mechanism."""
    print("\nTesting distributed locking...")
    repo = get_redis_repository("test")
    
    try:
        # Acquire lock
        with repo.distributed_lock("test_lock", timeout=5, blocking_timeout=2):
            print("✓ Lock acquired successfully")
            
            # Set some data while holding the lock
            repo.set_json("locked_data", {"status": "locked"})
            time.sleep(0.5)
            
            # Verify data
            data = repo.get_json("locked_data")
            if data["status"] == "locked":
                print("✓ Data operations under lock successful")
            else:
                print("✗ Data operations under lock failed")
                return False
        
        print("✓ Lock released successfully")
        
        # Clean up
        repo.delete("locked_data")
        return True
        
    except Exception as e:
        print(f"✗ Distributed locking failed: {e}")
        return False


def test_connection_pooling():
    """Test connection pooling."""
    print("\nTesting connection pooling...")
    
    # Create multiple repositories to test connection pooling
    repos = [get_redis_repository(f"pool_test_{i}") for i in range(5)]
    
    # Perform operations concurrently
    for i, repo in enumerate(repos):
        repo.set_json(f"pool_key_{i}", {"index": i}, ttl=60)
    
    # Verify all operations succeeded
    success = True
    for i, repo in enumerate(repos):
        data = repo.get_json(f"pool_key_{i}")
        if data is None or data["index"] != i:
            success = False
            break
        repo.delete(f"pool_key_{i}")
    
    if success:
        print("✓ Connection pooling working correctly")
    else:
        print("✗ Connection pooling test failed")
    
    return success


def main():
    """Run all infrastructure tests."""
    print("=" * 60)
    print("Core Infrastructure Test Suite")
    print("=" * 60)
    
    tests = [
        test_redis_connection,
        test_redis_operations,
        test_distributed_locking,
        test_connection_pooling,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
