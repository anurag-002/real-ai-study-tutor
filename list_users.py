#!/usr/bin/env python
"""
Simple script to list all users in the database
Run with: python list_users.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User

def list_users():
    users = User.objects.all()
    
    print(f"\n{'='*80}")
    print(f"Total Users: {users.count()}")
    print(f"{'='*80}\n")
    
    if users.count() == 0:
        print("No users found in database.\n")
        return
    
    for user in users:
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Is Staff: {user.is_staff}")
        print(f"Is Superuser: {user.is_superuser}")
        print(f"Date Joined: {user.date_joined}")
        print(f"Last Login: {user.last_login}")
        print("-" * 80)
    
    print()

if __name__ == '__main__':
    list_users()
