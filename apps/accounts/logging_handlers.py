import logging
import threading
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import SystemLog


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that saves log records to database"""
    
    def __init__(self):
        super().__init__()
        self.local = threading.local()
    
    def emit(self, record):
        """Save log record to database"""
        try:
            # Format the message
            message = self.format(record)
            
            # Get request info if available
            request_path = getattr(record, 'request_path', '')
            request_method = getattr(record, 'request_method', '')
            ip_address = getattr(record, 'ip_address', None)
            user_agent = getattr(record, 'user_agent', '')
            user = getattr(record, 'user', None)
            
            # Prepare extra data
            extra_data = {}
            if hasattr(record, 'extra'):
                extra_data.update(record.extra)
            
            # Add exception info if present
            if record.exc_info:
                extra_data['exception'] = self.formatException(record.exc_info)
            
            # Save to database in a separate transaction
            self._save_log_record(
                level=record.levelname,
                logger_name=record.name,
                message=message,
                pathname=record.pathname,
                funcName=record.funcName,
                lineno=record.lineno,
                user=user,
                request_path=request_path,
                request_method=request_method,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data=extra_data or None
            )
            
        except Exception as e:
            # Fallback to prevent infinite loops
            self.handleError(record)
    
    def _save_log_record(self, **kwargs):
        """Save log record to database with proper transaction handling"""
        try:
            # Use a separate database transaction to avoid issues
            with transaction.atomic():
                SystemLog.objects.create(**kwargs)
        except Exception:
            # If database is not available, fail silently
            pass


class DatabaseLoggerMiddleware:
    """Middleware to add request context to log records"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store request info in thread local for logging
        if hasattr(logging, '_thread_locals'):
            logging._thread_locals.request = request
        
        response = self.get_response(request)
        
        # Clean up thread local
        if hasattr(logging, '_thread_locals'):
            if hasattr(logging._thread_locals, 'request'):
                delattr(logging._thread_locals, 'request')
        
        return response


def add_request_context(record):
    """Add request context to log record"""
    if hasattr(logging, '_thread_locals') and hasattr(logging._thread_locals, 'request'):
        request = logging._thread_locals.request
        record.request_path = getattr(request, 'path', '')
        record.request_method = getattr(request, 'method', '')
        record.ip_address = get_client_ip(request)
        record.user_agent = request.META.get('HTTP_USER_AGENT', '')
        if hasattr(request, 'user') and request.user.is_authenticated:
            record.user = request.user
        else:
            record.user = None
    return record


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records"""
    
    def filter(self, record):
        add_request_context(record)
        return True