#!/usr/bin/env python
"""
Script to create initial users for SyncContents application
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialsync.settings')
django.setup()

from apps.accounts.models import User

def create_initial_users():
    """Create admin and test users"""
    
    # Create admin user
    admin_email = 'admin@synccontents.com'
    if not User.objects.filter(email=admin_email).exists():
        admin_user = User.objects.create_user(
            username='admin',
            email=admin_email,
            password='admin123',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
            is_verified=True
        )
        print(f"✅ Admin user created: {admin_email}")
    else:
        print(f"ℹ️  Admin user already exists: {admin_email}")
    
    # Create test user
    test_email = 'test@synccontents.com'
    if not User.objects.filter(email=test_email).exists():
        test_user = User.objects.create_user(
            username='testuser',
            email=test_email,
            password='test123',
            first_name='Test',
            last_name='User',
            is_verified=True
        )
        print(f"✅ Test user created: {test_email}")
    else:
        print(f"ℹ️  Test user already exists: {test_email}")
    
    print("\n📋 User Summary:")
    print("=" * 50)
    print("Admin User:")
    print(f"  Email: admin@synccontents.com")
    print(f"  Password: admin123")
    print(f"  Permissions: Staff + Superuser")
    print("\nTest User:")
    print(f"  Email: test@synccontents.com")
    print(f"  Password: test123")
    print(f"  Permissions: Regular user")
    print("=" * 50)

if __name__ == '__main__':
    create_initial_users()