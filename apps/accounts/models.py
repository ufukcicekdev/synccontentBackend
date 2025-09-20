from django.contrib.auth.models import AbstractUser
from django.db import models
import json


class User(AbstractUser):
    """Extended user model with additional fields for SocialSync Pro"""
    
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    subscription_tier = models.CharField(
        max_length=20,
        choices=[
            ('starter', 'Starter'),
            ('professional', 'Professional'),
            ('agency', 'Agency'),
            ('enterprise', 'Enterprise'),
        ],
        default='starter'
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email


class UserProfile(models.Model):
    """Extended profile information for users"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company_name = models.CharField(max_length=255, blank=True)
    website_url = models.URLField(blank=True)
    bio = models.TextField(max_length=500, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    marketing_emails = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email} Profile"


class SystemLog(models.Model):
    """System log entries stored in database"""
    
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    logger_name = models.CharField(max_length=100)
    message = models.TextField()
    pathname = models.CharField(max_length=500, blank=True)
    funcName = models.CharField(max_length=100, blank=True)
    lineno = models.IntegerField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    extra_data = models.JSONField(blank=True, null=True)
    
    class Meta:
        db_table = 'system_logs'
        ordering = ['-created']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['created']),
            models.Index(fields=['logger_name']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.level} - {self.logger_name} - {self.created.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def set_extra_data(self, data):
        """Set extra data with JSON serialization"""
        if data:
            self.extra_data = data if isinstance(data, dict) else {'data': str(data)}
            
    def get_extra_data(self):
        """Get extra data with safe JSON parsing"""
        return self.extra_data or {}