#!/bin/bash

# Entrypoint script for different service modes

set -e

case "$1" in
    "web")
        echo "Starting Flask web server..."
        exec python main.py
        ;;
    "worker")
        echo "Starting Celery worker..."
        exec celery -A celery_app.celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-2} --max-tasks-per-child=50
        ;;
    "beat")
        echo "Starting Celery beat scheduler..."
        exec celery -A celery_app.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
        ;;
    *)
        echo "Usage: $0 {web|worker|beat}"
        echo "Starting Flask web server by default..."
        exec python main.py
        ;;
esac