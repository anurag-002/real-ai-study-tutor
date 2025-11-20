"""
Django Backend Entry Point
This module initializes the Django application.

To run the server, use:
    python manage.py runserver 0.0.0.0:8000

The original FastAPI implementation is preserved in main_fastapi_backup.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()
