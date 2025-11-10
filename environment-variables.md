# Environment Variables Documentation

## Overview

This document lists all environment variables used in the UltraDL application, organized by component.

---

## Flask Application (backend/main.py)

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for rate limiting and storage |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_VERSION` | `v1` | API version for endpoint routing |
| `RATE_LIMIT_DAILY` | `200` | Maximum requests per day per IP |
| `RATE_LIMIT_HOURLY` | `50` | Maximum requests per hour per IP |
| `SOCKETIO_ENABLED` | `true` | Enable/disable WebSocket support |
| `FLASK_HOST` | `0.0.0.0` | Flask server host |
| `FLASK_PORT` | `8000` | Flask server port |
| `FLASK_DEBUG` | `true` | Enable Flask debug mode |

---

## Redis Configuration (backend/config/redis_config.py)

### Connection Options

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | - | Full Redis connection URL (overrides individual settings) |
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | - | Redis authentication password (optional) |
| `REDIS_MAX_CONNECTIONS` | `20` | Maximum Redis connection pool size |

---

## Celery Configuration (backend/config/celery_config.py)

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result backend URL |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_WORKER_CONCURRENCY` | `2` | Number of concurrent worker processes |

---

## Google Cloud Storage (backend/config/gcs_config.py)

### Optional Variables (Production Only)

| Variable | Default | Description |
|----------|---------|-------------|
| `GCS_BUCKET_NAME` | - | Google Cloud Storage bucket name |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to GCS service account JSON file |

**Note**: If not configured, system automatically falls back to local file storage.

---

## Socket.IO Configuration (backend/config/socketio_config.py)

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOCKETIO_ENABLED` | `true` | Enable/disable Socket.IO WebSocket support |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Socket.IO message queue |

---

## Job Management (backend/domain/job_management/repositories.py)

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_TTL_SECONDS` | `3600` | Job record TTL in Redis (1 hour) |

---

## File Storage (backend/domain/file_storage/signed_url_service.py)

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Auto-generated | Secret key for signed URL generation |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_BASE_URL` | - | Public-facing base URL for downloads (e.g., `http://localhost`) |
| `API_BASE_URL` | - | Internal API base URL (fallback if DOWNLOAD_BASE_URL not set) |

---

## Download Tasks (backend/tasks/download_task.py)

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FILE_TTL_MINUTES` | `10` | File expiration time in minutes |

---

## File Service (backend/application/file_service.py)

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | - | Base URL for constructing download URLs |

---

## Docker Compose Configuration

### Backend Service

```yaml
environment:
  # Flask Configuration
  - FLASK_ENV=development
  - FLASK_HOST=0.0.0.0
  - FLASK_PORT=8000
  - FLASK_DEBUG=true
  
  # API Configuration
  - API_VERSION=v1
  - API_BASE_URL=http://backend:8000
  - DOWNLOAD_BASE_URL=http://localhost
  
  # Python Configuration
  - PYTHONUNBUFFERED=1
  
  # Redis Configuration
  - REDIS_URL=redis://redis:6379/0
  
  # Celery Configuration
  - CELERY_BROKER_URL=redis://redis:6379/0
  - CELERY_RESULT_BACKEND=redis://redis:6379/0
  - CELERY_WORKER_CONCURRENCY=2
  
  # Rate Limiting
  - RATE_LIMIT_DAILY=200
  - RATE_LIMIT_HOURLY=50
  - RATE_LIMIT_STORAGE_URL=redis://redis:6379/0
  
  # Security
  - SECRET_KEY=dev-secret-key-change-in-production-use-openssl-rand-hex-32
  - CORS_ORIGINS=http://localhost,http://localhost:80,http://localhost:5000
  
  # File Management
  - FILE_TTL_MINUTES=10
  - JOB_TTL_SECONDS=3600
  - TEMP_DOWNLOAD_DIR=/tmp/ultra-dl
  
  # Logging
  - LOG_LEVEL=INFO
  
  # Google Cloud Storage (Optional)
  - GCS_BUCKET_NAME=
  - GOOGLE_APPLICATION_CREDENTIALS=
```

### Celery Worker Service

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - API_VERSION=v1
  - API_BASE_URL=http://backend:8000
  - DOWNLOAD_BASE_URL=http://localhost
  - REDIS_URL=redis://redis:6379/0
  - CELERY_BROKER_URL=redis://redis:6379/0
  - CELERY_RESULT_BACKEND=redis://redis:6379/0
  - CELERY_WORKER_CONCURRENCY=2
  - CELERY_LOG_LEVEL=INFO
  - SECRET_KEY=dev-secret-key-change-in-production-use-openssl-rand-hex-32
  - FILE_TTL_MINUTES=10
  - TEMP_DOWNLOAD_DIR=/tmp/ultra-dl
  - GCS_BUCKET_NAME=
```

### Celery Beat Service

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - API_VERSION=v1
  - API_BASE_URL=http://backend:8000
  - DOWNLOAD_BASE_URL=http://localhost
  - REDIS_URL=redis://redis:6379/0
  - CELERY_BROKER_URL=redis://redis:6379/0
  - CELERY_RESULT_BACKEND=redis://redis:6379/0
  - CELERY_LOG_LEVEL=INFO
```

### Frontend Service

```yaml
environment:
  - NODE_ENV=development
  - VITE_API_URL=http://localhost
  - VITE_API_VERSION=v1
  - API_BASE_URL=http://backend:8000
  - VITE_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
```

---

## Removed Variables (No Longer Used)

The following variables were removed during refactoring as they are no longer used:

| Variable | Reason for Removal |
|----------|-------------------|
| `CLEANUP_DELAY_SECONDS` | Old synchronous cleanup logic removed (replaced by Celery beat) |
| `MAX_RETURN_FILE_SIZE` | Never implemented, no size validation in code |

---

## Production Recommendations

### Security

1. **SECRET_KEY**: Generate a strong random key:
   ```bash
   openssl rand -hex 32
   ```

2. **CORS_ORIGINS**: Restrict to your actual domain:
   ```
   CORS_ORIGINS=https://yourdomain.com
   ```

3. **REDIS_PASSWORD**: Use password-protected Redis in production

### Performance

1. **CELERY_WORKER_CONCURRENCY**: Adjust based on server resources
2. **REDIS_MAX_CONNECTIONS**: Increase for high-traffic scenarios
3. **RATE_LIMIT_DAILY/HOURLY**: Adjust based on expected usage

### Storage

1. **GCS_BUCKET_NAME**: Configure for production file storage
2. **FILE_TTL_MINUTES**: Adjust based on user needs and storage costs
3. **JOB_TTL_SECONDS**: Balance between user convenience and Redis memory

---

## Environment Variable Validation

The application performs automatic validation and fallback:

1. **Redis**: Falls back to localhost if REDIS_URL not provided
2. **GCS**: Falls back to local storage if GCS not configured
3. **Socket.IO**: Falls back to polling if Socket.IO disabled
4. **API URLs**: Uses sensible defaults for development

---

## Troubleshooting

### Common Issues

1. **"Redis connection failed"**
   - Check `REDIS_URL` is correct
   - Verify Redis service is running
   - Check network connectivity

2. **"GCS not configured"**
   - This is normal in development
   - System automatically uses local storage
   - Configure `GCS_BUCKET_NAME` for production

3. **"Rate limit exceeded"**
   - Adjust `RATE_LIMIT_DAILY` and `RATE_LIMIT_HOURLY`
   - Check if rate limiter Redis connection is working

4. **"WebSocket connection failed"**
   - System automatically falls back to polling
   - Check `SOCKETIO_ENABLED` setting
   - Verify Redis is accessible for Socket.IO message queue
