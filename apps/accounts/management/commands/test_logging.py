import logging
from django.core.management.base import BaseCommand
from apps.accounts.models import SystemLog


class Command(BaseCommand):
    help = 'Test database logging functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing logs',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            count = SystemLog.objects.count()
            SystemLog.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Cleared {count} log entries')
            )
            return
        
        # Test different log levels
        logger = logging.getLogger('apps.accounts')
        
        # Create some test logs
        logger.info('Testing database logging functionality')
        logger.warning('This is a warning message')
        logger.error('This is an error message for testing')
        
        # Create log with extra data
        logger.info('Login attempt', extra={
            'user_id': 1,
            'ip_address': '127.0.0.1',
            'action': 'login_attempt'
        })
        
        # Check if logs were created
        recent_logs = SystemLog.objects.filter(
            logger_name='apps.accounts'
        ).order_by('-created')[:5]
        
        self.stdout.write(
            self.style.SUCCESS(f'Created test logs. Total logs in database: {SystemLog.objects.count()}')
        )
        
        for log in recent_logs:
            self.stdout.write(f'- {log.level}: {log.message[:50]}...')