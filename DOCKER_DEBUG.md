# Docker & Docker Compose Debugging Guide

## Quick Reference Commands

### 1. Container Status & Management

```bash
# List all containers (running and stopped)
docker compose ps -a

# Check service health status
docker compose ps

# Restart specific service
docker compose restart backend
docker compose restart celery-worker

# Stop all services
docker compose stop

# Start all services
docker compose start

# Restart all services
docker compose restart

# Stop and remove containers
docker compose down

# Stop, remove containers, and remove volumes (CAUTION: deletes data)
docker compose down -v
```

### 2. Viewing Logs

```bash
# View logs from all services
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View logs from specific service
docker compose logs backend
docker compose logs celery-worker
docker compose logs redis

# Follow logs from specific service
docker compose logs -f backend

# View last N lines of logs
docker compose logs --tail=50 backend

# View logs with timestamps
docker compose logs -t backend

# View logs from multiple services
docker compose logs backend celery-worker redis
```

### 3. Executing Commands Inside Containers

```bash
# Open interactive shell in backend container
docker compose exec backend bash

# Open interactive shell in celery-worker
docker compose exec celery-worker bash

# Run a command in backend container
docker compose exec backend python -c "print('Hello')"

# Check Python packages installed
docker compose exec backend pip list

# Run Django/Flask management commands
docker compose exec backend python main.py

# Access Redis CLI
docker compose exec redis redis-cli

# Check Redis keys
docker compose exec redis redis-cli KEYS "*"
```

### 4. Inspecting Container Details

```bash
# View container configuration
docker inspect backend

# View container IP address
docker inspect backend | grep IPAddress

# View container environment variables
docker compose exec backend env

# Check container processes
docker compose top backend

# Check all container processes
docker compose top
```

### 5. Resource Monitoring

```bash
# View real-time resource usage (CPU, Memory, Network, I/O)
docker stats

# View resource usage snapshot
docker stats --no-stream

# Monitor specific containers
docker stats backend celery-worker redis
```

### 6. Network Debugging

```bash
# List Docker networks
docker network ls

# Inspect network details
docker network inspect ultra-dl_default

# Test connectivity between containers
docker compose exec backend ping redis
docker compose exec backend ping celery-worker

# Check open ports in container
docker compose exec backend netstat -tulpn

# Test HTTP endpoint from inside container
docker compose exec backend curl http://localhost:8000/health
```

### 7. Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect ultra-dl_redis_data

# Check disk usage
docker system df

# Clean up unused volumes (CAUTION)
docker volume prune
```

### 8. Building & Rebuilding

```bash
# Rebuild specific service
docker compose build backend

# Rebuild all services
docker compose build

# Rebuild without cache
docker compose build --no-cache backend

# Build and start services
docker compose up -d --build

# Rebuild specific service and restart
docker compose up -d --build backend
```

### 9. Advanced Debugging

```bash
# View service configuration
docker compose config

# Validate docker-compose.yml
docker compose config --quiet

# View environment variables for service
docker compose config | grep -A 20 "backend:"

# Check container exit code
docker compose ps -a

# View container file system changes
docker diff backend

# Copy files from container to host
docker compose cp backend:/app/logs/error.log ./error.log

# Copy files from host to container
docker compose cp ./config.py backend:/app/config.py
```

### 10. Celery-Specific Debugging

```bash
# Check Celery worker status
docker compose exec celery-worker celery -A celery_app inspect active

# Check registered tasks
docker compose exec celery-worker celery -A celery_app inspect registered

# Check scheduled tasks
docker compose exec celery-worker celery -A celery_app inspect scheduled

# Check Celery stats
docker compose exec celery-worker celery -A celery_app inspect stats

# Purge all tasks from queue
docker compose exec celery-worker celery -A celery_app purge

# Monitor Celery events
docker compose exec celery-worker celery -A celery_app events
```

### 11. Redis Debugging

```bash
# Access Redis CLI
docker compose exec redis redis-cli

# Check all keys
docker compose exec redis redis-cli KEYS "*"

# Get specific key value
docker compose exec redis redis-cli GET "job:123"

# Check Redis info
docker compose exec redis redis-cli INFO

# Monitor Redis commands in real-time
docker compose exec redis redis-cli MONITOR

# Check memory usage
docker compose exec redis redis-cli INFO memory

# Flush all Redis data (CAUTION: deletes all data)
docker compose exec redis redis-cli FLUSHALL
```

### 12. Common Troubleshooting Scenarios

#### Container won't start
```bash
# Check logs for errors
docker compose logs backend

# Check if port is already in use
sudo netstat -tulpn | grep :8000

# Rebuild the container
docker compose up -d --build backend
```

#### Container keeps restarting
```bash
# View exit code and status
docker compose ps -a

# Check recent logs
docker compose logs --tail=100 backend

# Check health check status
docker inspect backend | grep -A 10 Health
```

#### Connection issues between containers
```bash
# Test connectivity
docker compose exec backend ping redis

# Check network
docker network inspect ultra-dl_default

# Verify service names in docker-compose.yml
docker compose config
```

#### Memory or CPU issues
```bash
# Check resource usage
docker stats

# Limit resources in docker-compose.yml (add under service):
# deploy:
#   resources:
#     limits:
#       cpus: '0.5'
#       memory: 512M
```

#### Application errors
```bash
# Check application logs
docker compose logs -f backend

# Access container shell to debug
docker compose exec backend bash

# Check environment variables
docker compose exec backend env

# Run Python debugger
docker compose exec backend python -m pdb main.py
```

### 13. Clean Up Commands

```bash
# Remove stopped containers
docker compose rm

# Remove all stopped containers, networks, and dangling images
docker system prune

# Remove everything including volumes (CAUTION)
docker system prune -a --volumes

# Remove specific service container
docker compose rm -f backend
```

## Tips for Effective Debugging

1. **Always check logs first**: `docker compose logs -f [service]`
2. **Use health checks**: Ensure services have health checks configured
3. **Test in isolation**: Test one service at a time when debugging
4. **Use exec for live debugging**: `docker compose exec [service] bash`
5. **Monitor resources**: Use `docker stats` to identify resource issues
6. **Check environment variables**: Ensure all required env vars are set
7. **Rebuild when needed**: After code changes, rebuild with `docker compose up -d --build`
8. **Use named volumes**: For data persistence across container restarts

## Current Service Status

Based on your running containers:

- ✅ **backend**: Running and healthy (Port 8000)
- ✅ **celery-worker**: Running and healthy
- ✅ **celery-beat**: Running (scheduler)
- ✅ **redis**: Running and healthy (Port 6379)
- ✅ **frontend**: Running (Port 5000)
- ✅ **traefik**: Running and healthy (Port 80)

All services are currently operational!
