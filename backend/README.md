# Backend - Flask API with Celery

Python backend using Flask for REST API and Celery for asynchronous video processing.

## Quick Start

```bash
# Start all services
docker-compose up backend celery-worker celery-beat redis

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Health check
curl http://localhost:8000/api/v1/system/health
```

## Architecture

**Domain-Driven Design (DDD)** with clean architecture. See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed patterns and diagrams.

```
backend/
├── domain/              # Business logic (zero external dependencies)
│   ├── job_management/  # Job entities, services, repositories
│   ├── file_storage/    # File entities, services, repositories
│   └── video_processing/# Video processing domain
├── application/         # Use case orchestration
│   ├── job_service.py   # Job management workflows
│   ├── video_service.py # Video processing workflows
│   └── event_publisher.py # Domain event dispatching
├── infrastructure/      # External integrations
│   ├── redis_*_repository.py # Redis implementations
│   ├── gcs_repository.py     # GCS storage
│   └── local_file_repository.py # Local storage
├── api/v1/              # REST endpoints (Flask-RESTX)
├── tasks/               # Celery background tasks
├── config/              # Configuration modules
├── app_factory.py       # Application factory pattern
├── main.py              # Flask entry point
└── celery_app.py        # Celery worker entry point
```

**Layer Dependencies:** Domain → Application → Infrastructure → API

**Key Patterns:**
- Repository interfaces in domain, implementations in infrastructure
- Domain events for decoupling side effects (WebSocket, logging)
- Service locator for accessing services from tasks/endpoints
- Value objects for type safety (FormatId, DownloadToken, YouTubeUrl)
- Batch operations for efficient multi-job queries (5x faster)

**Development Workflow:** See [AGENTS.md](./AGENTS.md) for DDD patterns and testing guidelines.

## Tech Stack

- **Flask 3.1.2** - Web framework
- **Celery 5.5.3** - Distributed task queue
- **Redis 7.0.1** - Job persistence and broker
- **yt-dlp** - YouTube video downloader
- **Flask-RESTX** - API documentation (Swagger)
- **Flask-SocketIO** - WebSocket support
- **Google Cloud Storage** - File storage (optional)

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Environment mode (development/production) |
| `FLASK_HOST` | `0.0.0.0` | Server host |
| `FLASK_PORT` | `8000` | Server port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Result backend |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOCKETIO_ENABLED` | `true` | Enable WebSocket notifications |
| `GCS_ENABLED` | `false` | Enable Google Cloud Storage (production) |
| `GCS_BUCKET_NAME` | - | GCS bucket name (required if GCS_ENABLED=true) |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Service account JSON path |

### Rate Limiting Configuration

Rate limiting is **only enforced in production** (`FLASK_ENV=production`). Development and testing environments bypass all limits.

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `RATE_LIMIT_VIDEO_ONLY_DAILY` | `20` | Video-without-audio downloads per day per IP |
| `RATE_LIMIT_AUDIO_ONLY_DAILY` | `20` | Audio-only downloads per day per IP |
| `RATE_LIMIT_VIDEO_AUDIO_DAILY` | `20` | Video-with-audio downloads per day per IP |
| `RATE_LIMIT_TOTAL_JOBS_DAILY` | `60` | Total download jobs per day per IP (all types) |
| `RATE_LIMIT_ENDPOINT_HOURLY` | - | Endpoint-specific hourly limits (format: `endpoint:limit,endpoint:limit`) |
| `RATE_LIMIT_BATCH_MINUTE` | `10` | Requests per minute per IP (burst protection) |
| `RATE_LIMIT_WHITELIST` | - | Comma-separated IP addresses exempt from limits |

**Example Configuration:**

```bash
# Enable rate limiting (production only)
RATE_LIMIT_ENABLED=true
FLASK_ENV=production

# Per-video-type daily limits
RATE_LIMIT_VIDEO_ONLY_DAILY=20
RATE_LIMIT_AUDIO_ONLY_DAILY=20
RATE_LIMIT_VIDEO_AUDIO_DAILY=20

# Total daily limit across all types
RATE_LIMIT_TOTAL_JOBS_DAILY=60

# Endpoint-specific hourly limits
RATE_LIMIT_ENDPOINT_HOURLY=/api/v1/videos/resolutions:100,/api/v1/downloads/:50

# Burst protection (per-minute limit)
RATE_LIMIT_BATCH_MINUTE=10

# Whitelist internal IPs
RATE_LIMIT_WHITELIST=127.0.0.1,10.0.0.1,192.168.1.100
```

**Production-Only Enforcement:**
- Rate limiting **only** enforces when `FLASK_ENV=production`
- Development (`FLASK_ENV=development`) bypasses all limits
- Testing environments bypass all limits
- Allows unlimited requests during development and testing

## API Endpoints

**Base URL:** `http://localhost:8000/api/v1`  
**Documentation:** `http://localhost:8000/api/v1/docs` (Swagger)

### Videos
- `POST /videos/resolutions` - Get available formats for URL

### Downloads
- `POST /downloads/` - Create download job
- `GET /jobs/{job_id}` - Get job status
- `DELETE /jobs/{job_id}` - Cancel/delete job
- `GET /downloads/file/{token}` - Download file

### System
- `GET /system/health` - Health check

**Response Codes:** 200 (OK), 202 (Accepted), 400 (Bad Request), 404 (Not Found), 410 (Gone), 429 (Rate Limited), 500 (Server Error)

## WebSocket Events

**Client → Server:**
- `subscribe_job` - Subscribe to job updates
- `unsubscribe_job` - Unsubscribe from job
- `cancel_job` - Cancel job

**Server → Client:**
- `job_progress` - Progress updates (percentage, speed, ETA)
- `job_completed` - Completion notification
- `job_failed` - Failure notification
- `job_cancelled` - Cancellation confirmation

## Development

### Run Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Flask server
python main.py

# Start Celery worker (separate terminal)
celery -A celery_app worker --loglevel=info

# Start Celery beat (separate terminal)
celery -A celery_app beat --loglevel=info
```

### Run with Docker

```bash
# Start backend only
docker-compose up backend

# Start with workers
docker-compose up backend celery-worker celery-beat redis

# Rebuild after code changes
docker-compose up --build backend
```

## Testing

### Test Structure

Tests are organized by type in the `tests/` directory:

```
tests/
├── unit/                    # Fast, isolated tests (domain, application logic)
│   ├── test_domain_units.py
│   ├── test_value_objects.py
│   ├── test_job_service.py
│   ├── test_download_service.py
│   ├── test_service_locator.py
│   └── test_dependency_container.py
├── integration/             # Tests with external services (Redis, GCS, API)
│   ├── test_infrastructure.py
│   ├── test_redis_*.py
│   ├── test_gcs_*.py
│   ├── test_local_file_storage.py
│   ├── test_event_handlers.py
│   ├── test_event_publisher.py
│   ├── test_api_integration.py
│   ├── test_simplified_download_task.py
│   ├── test_batch_operations.py
│   └── test_app_factory.py
├── contracts/               # Repository interface compliance tests
│   └── test_repository_contracts.py
└── e2e/                     # End-to-end workflow tests
├── performance/             # Performance and latency tests
```

### Run Tests

```bash
# Run all tests with coverage
docker-compose exec backend python -m pytest --cov=. --cov-report=html --cov-report=term-missing

# Run by test type
docker-compose exec backend python -m pytest tests/unit/              # Unit tests only (fast)
docker-compose exec backend python -m pytest tests/integration/       # Integration tests only
docker-compose exec backend python -m pytest tests/contracts/         # Contract tests only
docker-compose exec backend python -m pytest tests/e2e/              # E2E tests only
n# Run performance tests
docker-compose exec backend python -m pytest tests/performance/ -v -s  # Performance tests (p95 latency)

# Run specific test file
docker-compose exec backend python -m pytest tests/unit/test_job_service.py -v

# Run with markers (if configured)
docker-compose exec backend python -m pytest -m unit                  # Unit tests
docker-compose exec backend python -m pytest -m integration           # Integration tests
docker-compose exec backend python -m pytest -m performance          # Performance tests
docker-compose exec backend python -m pytest -m "not integration"     # Skip integration tests

# Generate coverage report
docker-compose exec backend python generate_coverage.py

# View HTML coverage report (after running tests with --cov-report=html)
# Open backend/htmlcov/index.html in your browser
```

**Viewing Coverage Reports:**

After running tests with coverage, open the HTML report to see detailed line-by-line coverage:

```bash
# Generate HTML coverage report
docker-compose exec backend python -m pytest --cov=. --cov-report=html

# The report is generated at: backend/htmlcov/index.html
# Open this file in your browser to view:
# - Overall coverage statistics
# - Per-module coverage breakdown
# - Line-by-line coverage highlighting
# - Missing lines and branches
```

The HTML report provides:
- Color-coded coverage visualization (green = covered, red = missing)
- Sortable tables by coverage percentage
- Drill-down into individual files
- Context for uncovered lines

### Test Fixtures

The test suite uses shared fixtures defined in `tests/conftest.py` for consistent test data and mocking:

**Application Context Fixtures:**
- `app` - Flask application instance with test configuration
- `client` - Flask test client for API requests
- `app_context` - Active Flask application context

**Infrastructure Fixtures:**
- `redis_client` - Fake Redis client (in-memory, auto-flushed)
- `temp_storage_dir` - Temporary directory for file operations
- `mock_socketio` - Mock SocketIO for WebSocket testing

**Domain Entity Fixtures:**
- `sample_job` - Basic DownloadJob in PENDING status
- `sample_progress` - JobProgress at 50% completion
- `sample_file` - DownloadFile entity with test data
- `sample_token` - Valid DownloadToken for file access

**Test Data Builders:**
- `JobBuilder` - Fluent interface for creating custom jobs
  ```python
  job = JobBuilder().with_id('test').completed().build()
  ```

**Mock Service Fixtures:**
- `mock_job_repository` - Mock JobRepository with stubs
- `mock_file_repository` - Mock FileRepository with stubs
- `mock_event_publisher` - Mock EventPublisher for domain events

See `tests/conftest.py` for complete fixture documentation and usage examples.

### Test Types

**Unit Tests** (`tests/unit/`)
- Test domain entities, value objects, and services
- Test application services and orchestration logic
- No external dependencies (Redis, GCS, file system)
- Fast execution (< 1 second per test)
- Use mocks/stubs for external dependencies
- **Domain tests:** Mock `IVideoMetadataExtractor` interface
- **Application tests:** Mock domain services and event publisher

**Integration Tests** (`tests/integration/`)
- Test infrastructure implementations with real services
- Test Redis repositories with actual Redis connection
- Test GCS repositories with actual GCS or emulator
- Test API endpoints with Flask test client
- Test Celery tasks with task execution
- Test `VideoMetadataExtractor` with real yt-dlp calls
- Slower execution (may take seconds per test)

**Contract Tests** (`tests/contracts/`)
- Verify repository implementations comply with domain interfaces
- Test that all interface methods are implemented
- Test that implementations follow interface contracts
- **Example:** `MetadataExtractorContractTest` verifies `VideoMetadataExtractor` implements `IVideoMetadataExtractor`
- Ensures infrastructure implementations satisfy domain contracts

**E2E Tests** (`tests/e2e/`)
- Test complete user workflows through API
- Test full download flow from URL submission to file retrieval
- Test error scenarios end-to-end
- Slowest execution (may take minutes)

### Testing DDD Architecture

**Domain Layer Testing:**
```python
# Test VideoProcessor with mocked IVideoMetadataExtractor
def test_extract_metadata(mock_extractor):
    processor = VideoProcessor(mock_extractor)
    mock_extractor.extract_metadata.return_value = VideoMetadata(...)
    
    result = processor.extract_metadata("https://youtube.com/watch?v=test")
    
    assert result.id == "test"
    mock_extractor.extract_metadata.assert_called_once()
```

**Infrastructure Layer Testing:**
```python
# Test VideoMetadataExtractor with real yt-dlp
@pytest.mark.integration
def test_extract_metadata_real_video():
    extractor = VideoMetadataExtractor()
    url = YouTubeUrl("https://www.youtube.com/watch?v=jNQXAC9IVRw")
    
    metadata = extractor.extract_metadata(url)
    
    assert metadata.id == "jNQXAC9IVRw"
    assert metadata.title is not None
```

**Contract Testing:**
```python
# Verify VideoMetadataExtractor implements IVideoMetadataExtractor
class TestVideoMetadataExtractorContract(MetadataExtractorContractTest):
    @pytest.fixture
    def extractor(self):
        return VideoMetadataExtractor()
```

**Coverage:** 81% overall (474 tests, ~42s execution time)

**Module Coverage Highlights:**
- Domain Layer: 85-100% (business logic well-tested)
- Application Services: 81-99% (core workflows covered)
- Infrastructure: 75-93% (Redis, storage, caching)
- API Endpoints: 67% (core paths tested, some error paths pending)
- WebSocket Events: 59% (emitters tested, handlers need work)

**Coverage by Test Type:**
- Unit Tests: 270+ tests (domain, application, value objects)
- Integration Tests: 150+ tests (Redis, storage, API, tasks)
- E2E Tests: 25+ tests (complete workflows)
- Performance Tests: 3 tests (p95 latency validation)
- Contract Tests: 2 tests (repository interface compliance)

### Test Quality Metrics

✅ **All quality metrics PASSED** (see [test_quality_metrics_report.md](./test_quality_metrics_report.md))

- **Execution Speed:** 41.8 seconds (target: < 120 seconds) - 65% under target
- **Test Isolation:** VERIFIED - Tests pass in any order (pytest-randomly)
- **Flaky Tests:** 0% - All tests produce consistent results across runs
- **Naming Convention:** COMPLIANT - All tests follow `test_<action>_<expected_result>` pattern

**Test Isolation Verification:**
```bash
# Run tests in random order to verify isolation
docker-compose exec backend python -m pytest -p randomly -q
```

**Flaky Test Detection:**
```bash
# Run tests multiple times to check for flakiness
docker-compose exec backend bash -c "python -m pytest -q --tb=no && python -m pytest -q --tb=no"
```

## Storage Strategy

### Development
- Local filesystem: `/tmp/ultra-dl/`
- Redis token mapping
- Celery cleanup tasks (15-minute retention)

### Production
- Google Cloud Storage (primary)
- Signed URLs (10-minute expiration)
- GCS lifecycle rules (1-day retention)
- Automatic fallback to local storage

## Rate Limiting Usage

### Decorator-Based Rate Limiting

Apply rate limiting to endpoints using the `@rate_limit` decorator:

```python
from api.rate_limit_decorator import rate_limit

# Apply endpoint-specific hourly limit
@api.route('/videos/resolutions', methods=['POST'])
@rate_limit(limit_types=['hourly', 'per_minute'])
def get_resolutions():
    # Endpoint logic
    return jsonify(formats)
```

### Manual Rate Limit Checks

For complex scenarios (like download endpoint with multiple limit types):

```python
from application.service_locator import get_rate_limit_service
from api.rate_limit_decorator import extract_client_ip

@api.route('/downloads/', methods=['POST'])
def create_download():
    # Get rate limit service
    rate_limit_service = get_rate_limit_service()
    
    # Extract client IP
    client_ip = extract_client_ip(request)
    
    # Determine video type from format_id
    video_type = determine_video_type(format_id)  # 'video-only', 'audio-only', 'video-audio'
    
    try:
        # Check all applicable limits (per-minute, per-type, total daily)
        entities = rate_limit_service.check_download_limits(client_ip, video_type)
        
        # Execute business logic
        job = download_service.create_job(url, format_id)
        
        # Add rate limit headers from most restrictive limit
        most_restrictive = rate_limit_service.get_most_restrictive_entity(entities)
        
        return jsonify(job), 202, most_restrictive.to_headers()
        
    except RateLimitExceededError as e:
        # Return HTTP 429 with error details
        return jsonify({
            'error': 'Rate limit exceeded',
            'limit_type': e.context.get('limit_type'),
            'reset_at': e.context.get('reset_at')
        }), 429
```

### Rate Limit Headers

All responses include standard rate limit headers:

```http
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1699920000
```

- `X-RateLimit-Limit` - Maximum requests in current window
- `X-RateLimit-Remaining` - Requests remaining in current window
- `X-RateLimit-Reset` - Unix timestamp when limit resets

### IP Whitelisting

Whitelist specific IPs to bypass all rate limits:

```bash
# Whitelist internal services and monitoring tools
RATE_LIMIT_WHITELIST=127.0.0.1,10.0.0.1,192.168.1.100
```

Whitelisted IPs bypass all rate limit checks and receive unlimited access.

## Dependency Injection

Access application services through the `DependencyContainer`:

```python
from application.dependency_container import get_container

# In Celery tasks
@celery_app.task(bind=True)
def download_video(self, job_id: str, url: str, format_id: str):
    container = get_container()
    download_service = container.get_download_service()
    
    def progress_callback(progress):
        self.update_state(state='PROGRESS', meta=progress.to_dict())
    
    result = download_service.execute_download(job_id, url, format_id, progress_callback)
    return result.to_dict()

# In API endpoints
@api.route('/jobs/<job_id>')
def get_job(job_id: str):
    container = get_container()
    job_service = container.get_job_service()
    status = job_service.get_job_status(job_id)
    return jsonify(status)
```

**Available Services:**
- `get_download_service()` - Video download workflows
- `get_job_service()` - Job management operations
- `get_video_service()` - Video processing operations
- `get_event_publisher()` - Domain event publishing

**Benefits:**
- Explicit dependencies (no hidden dependencies)
- Easy to test with mocked services
- Centralized service initialization
- Follows dependency injection best practices

## Application Factory Pattern

Create Flask app with dependency injection:

```python
# Production (main.py)
from app_factory import create_app
app = create_app()

# Testing (with custom config)
from app_factory import create_app, AppConfig
config = AppConfig()
config.is_production = False
app = create_app(config)
```

**Benefits:**
- Easy test instance creation with mock dependencies
- Configuration override for different environments
- Centralized dependency injection
- Proper service initialization in app context

## Troubleshooting

```bash
# Check services
curl http://localhost:8000/api/v1/system/health
docker-compose exec redis redis-cli ping
docker-compose exec celery-worker celery -A celery_app inspect active

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

**Common Issues:**
- **Redis Connection:** Verify Redis is running (`docker-compose ps redis`), check `REDIS_URL`
- **Celery Tasks:** Check worker status (`docker-compose ps celery-worker`), verify `CELERY_BROKER_URL`
- **Download Failures:** Verify URL is valid, check error category in job status (VIDEO_UNAVAILABLE, GEO_BLOCKED)
- **File Not Found (410):** Files expire after 15 minutes (dev) or 1 day (prod)

### Rate Limiting Troubleshooting

**Rate Limit Not Enforcing:**
1. Check `FLASK_ENV` is set to `production`
2. Verify `RATE_LIMIT_ENABLED=true`
3. Check Redis connection: `docker-compose exec redis redis-cli ping`
4. View rate limit logs: `docker-compose logs backend | grep "rate limit"`

**Unexpected HTTP 429 Responses:**
1. Check current limit counters in Redis:
   ```bash
   docker-compose exec redis redis-cli KEYS "ratelimit:*"
   docker-compose exec redis redis-cli GET "ratelimit:daily_total:{ip_hash}"
   ```
2. Check TTL (time until reset):
   ```bash
   docker-compose exec redis redis-cli TTL "ratelimit:daily_total:{ip_hash}"
   ```
3. Manually reset counter (testing only):
   ```bash
   docker-compose exec redis redis-cli DEL "ratelimit:daily_total:{ip_hash}"
   ```

**Whitelist Not Working:**
1. Verify IP format in `RATE_LIMIT_WHITELIST` (comma-separated, no spaces)
2. Check IP extraction: `docker-compose logs backend | grep "Client IP"`
3. Verify whitelist is loaded: Check startup logs for "Rate limit whitelist"

**Redis Connection Failures:**
- Rate limiting gracefully degrades when Redis is unavailable
- Requests proceed without rate limiting (fail-open behavior)
- Check logs for "Redis error in rate limiting" messages
- Verify Redis is healthy: `docker-compose ps redis`

**Performance Issues:**
- Rate limiting adds <5ms overhead per request
- Redis operations use 1-second timeout
- Check Redis latency: `docker-compose exec redis redis-cli --latency`
- Monitor Redis memory: `docker-compose exec redis redis-cli INFO memory`

## Performance Monitoring

The backend uses standard logging and external tools for performance monitoring. No custom performance middleware is implemented to keep the codebase lean.

### Running Performance Tests

**Load Testing with Apache Bench:**

```bash
# Test health endpoint (1000 requests, concurrency 10)
docker-compose exec backend ab -n 1000 -c 10 http://localhost:8000/health

# Test system health endpoint
docker-compose exec backend ab -n 1000 -c 10 http://localhost:8000/api/v1/system/health

# Test video resolutions endpoint (requires valid URL)
docker-compose exec backend ab -n 100 -c 5 "http://localhost:8000/api/v1/videos/resolutions?url=https://youtube.com/watch?v=test"
```

**Interpreting Results:**
- Look for p95 (95th percentile) response time
- Target: <200ms for all endpoints
- Check "Requests per second" for throughput
- Monitor "Failed requests" (should be 0)

**Alternative Load Testing Tools:**
- **Locust**: Python-based load testing with web UI
- **wrk**: Modern HTTP benchmarking tool
- **k6**: Developer-centric load testing tool

### Monitoring Cache Performance

**Check Redis Cache Statistics:**

```bash
# View cache hit/miss rates
docker-compose exec redis redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"

# Calculate cache hit rate
docker-compose exec redis redis-cli INFO stats | awk '/keyspace_hits/{hits=$2} /keyspace_misses/{misses=$2} END {print "Hit rate:", hits/(hits+misses)*100"%"}'
```

### Application Logging

Performance metrics are captured through standard Flask and Celery logging:
- Request duration logged by Flask
- Task execution time logged by Celery workers
- Cache operations logged by RedisCacheService
- Use `docker-compose logs -f backend` to monitor application logs

# View cached keys
docker-compose exec redis redis-cli KEYS "video:*"

# Check TTL for a specific key
docker-compose exec redis redis-cli TTL "video:metadata:abc123"

# Monitor Redis operations in real-time
docker-compose exec redis redis-cli MONITOR
```

**Cache Performance Targets:**
- Video metadata cache hit rate: >70%
- Overall cache hit rate: >25%
- TTL: 300 seconds (5 minutes)

### Analyzing Performance Logs

**View Performance Metrics:**

```bash
# View recent API request logs
docker-compose logs backend --tail 100 | grep '"type":"api_request"'

# View cache hit/miss logs
docker-compose logs backend --tail 100 | grep '"type":"cache_'

# View task duration logs
docker-compose logs backend --tail 100 | grep '"type":"task_duration"'
```

**Monitor Task Execution:**

```bash
# View task execution logs
docker-compose logs celery-worker | grep "Task started\|Task completed\|Task failed"

# Monitor task performance
docker-compose logs celery-worker | grep "duration"
```

### Monitoring Redis Pipeline Efficiency

**Check Pipeline Usage:**

```bash
# View Redis command statistics
docker-compose exec redis redis-cli INFO commandstats

# Look for pipeline commands (should see fewer GET/SET calls)
docker-compose exec redis redis-cli INFO commandstats | grep -E "cmdstat_get|cmdstat_set|cmdstat_pipeline"
```

**Pipeline Benefits:**
- 90% reduction in round-trips for batch operations
- Faster multi-job queries
- Reduced network latency

### Performance Baseline Comparison

**View Current Metrics:**

```bash
# View baseline metrics file
cat backend/BASELINE_METRICS.md

# Run load tests and compare to baseline
docker-compose exec backend ab -n 1000 -c 10 http://localhost:8000/health | grep "95%"
```

**Metrics to Track:**
- API response times (p50, p95, p99)
- Cache hit rates
- Redis pipeline efficiency
- Task durations
- Requests per second

### Troubleshooting Performance Issues

**Slow API Responses:**
1. Check performance logs for slow endpoints
2. Verify cache is working (check Redis stats)
3. Profile the endpoint with cProfile
4. Check for N+1 queries or missing pipelines
5. Verify Redis connection is healthy

**Low Cache Hit Rate:**
1. Check TTL settings (should be 300s)
2. Verify cache keys are being set correctly
3. Check for cache eviction (Redis memory)
4. Monitor cache miss patterns
5. Adjust TTL if needed

**Slow Celery Tasks:**
1. Enable task profiling
2. Check for operations >1000ms
3. Optimize yt-dlp configuration
4. Verify external API performance
5. Check network latency

### Continuous Monitoring

**Set Up Alerts:**
- API p95 response time >200ms
- Cache hit rate <70%
- Task duration >15 seconds
- Redis memory usage >80%

**Regular Checks:**
- Daily: Review performance logs
- Weekly: Run load tests and compare to baseline
- Monthly: Analyze cache hit rates and optimize TTL
- Quarterly: Profile tasks and optimize bottlenecks

## Additional Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete DDD patterns, diagrams, and performance optimization strategies
- **[BASELINE_METRICS.md](./BASELINE_METRICS.md)** - Performance baseline and optimization results
- **[AGENTS.md](./AGENTS.md)** - Development workflow and testing guidelines
