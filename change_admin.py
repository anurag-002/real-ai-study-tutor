#!/usr/bin/env python
"""Quick script to change superuser password"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User

username = input("Enter superuser username: ")
try:
    user = User.objects.get(username=username)
    new_password = input("Enter new password: ")
    user.set_password(new_password)
    user.save()
    print(f"✅ Password changed successfully for '{username}'!")
except User.DoesNotExist:
    print(f"❌ User '{username}' not found!")
