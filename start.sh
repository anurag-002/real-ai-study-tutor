#!/bin/bash
# Startup script for Render

echo "Ensuring data directory exists..."
mkdir -p /opt/render/project/src/data

echo "Running database migrations..."
python manage.py migrate --run-syncdb

echo "Starting gunicorn..."
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120
