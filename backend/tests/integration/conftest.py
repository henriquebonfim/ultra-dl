
import pytest
import redis
import os

@pytest.fixture
def redis_client():
    """
    Yields a clean Redis client for integration testing.
    Connects to the redis service defined in docker-compose.yml.
    """
    # Use environment variables or defaults matching docker-compose
    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", 6379))
    db = int(os.getenv("REDIS_DB", 0))

    client = redis.Redis(host=host, port=port, db=db, decode_responses=False)

    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis service not available. Skipping integration tests.")

    # Clean before test
    client.flushdb()

    yield client

    # Clean after test
    client.flushdb()
    client.close()
