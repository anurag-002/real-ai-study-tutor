#!/bin/bash
# Startup script for Render

echo "Ensuring data directory exists..."
mkdir -p /opt/render/project/src/data

echo "Running database migrations..."
python manage.py migrate --run-syncdb

echo "Starting gunicorn with optimized settings..."
exec gunicorn backend.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 1 \
  --threads 2 \
  --timeout 300 \
  --worker-class sync \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --preload
