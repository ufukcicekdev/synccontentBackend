#!/usr/bin/env python
"""
Simple utility to log messages directly to database
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialsync.settings')
django.setup()

from apps.accounts.models import SystemLog

def log_to_database(level, logger_name, message, user=None, extra_data=None):
    """Log a message to the database"""
    try:
        log_entry = SystemLog.objects.create(
            level=level,
            logger_name=logger_name,
            message=message,
            user=user,
            extra_data=extra_data
        )
        print(f"✅ Log created: {log_entry}")
        return log_entry
    except Exception as e:
        print(f"❌ Failed to create log: {e}")
        return None

if __name__ == '__main__':
    # Test logging
    log_to_database('INFO', 'test.logger', 'Database logging is working!')
    log_to_database('WARNING', 'test.logger', 'This is a warning message')
    log_to_database('ERROR', 'test.logger', 'This is an error message', extra_data={'test': True})
    
    # Show recent logs
    recent_logs = SystemLog.objects.order_by('-created')[:5]
    print(f"\n📊 Recent logs ({len(recent_logs)}):")
    for log in recent_logs:
        print(f"  - {log.level}: {log.message} ({log.created})")