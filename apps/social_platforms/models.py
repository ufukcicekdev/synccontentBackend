from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import json

User = get_user_model()


class SocialPlatform(models.Model):
    """Model to define available social media platforms"""
    
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('twitter', 'Twitter/X'),
    ]
    
    name = models.CharField(max_length=50, choices=PLATFORM_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=100, help_text='CSS class for platform icon')
    color_class = models.CharField(max_length=100, help_text='CSS class for platform color')
    is_active = models.BooleanField(default=True)
    oauth_client_id = models.CharField(max_length=255, blank=True)
    oauth_client_secret = models.CharField(max_length=255, blank=True)
    oauth_authorization_url = models.URLField(blank=True)
    oauth_token_url = models.URLField(blank=True)
    oauth_scope = models.TextField(blank=True, help_text='Comma-separated scopes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_platforms'
        verbose_name = 'Social Platform'
        verbose_name_plural = 'Social Platforms'
    
    def __str__(self):
        return self.display_name


class UserSocialAccount(models.Model):
    """Model to store user's connected social media accounts"""
    
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('expired', 'Token Expired'),
        ('revoked', 'Access Revoked'),
        ('error', 'Connection Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.ForeignKey(SocialPlatform, on_delete=models.CASCADE)
    platform_user_id = models.CharField(max_length=255, help_text='User ID on the social platform')
    platform_username = models.CharField(max_length=255, blank=True)
    platform_display_name = models.CharField(max_length=255, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True)
    
    # Encrypted tokens for security
    access_token = models.TextField(help_text='Encrypted access token')
    refresh_token = models.TextField(blank=True, help_text='Encrypted refresh token')
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='connected')
    permissions = models.JSONField(default=dict, help_text='Platform-specific permissions')
    
    # OAuth metadata
    oauth_state = models.CharField(max_length=255, blank=True)
    oauth_code_verifier = models.CharField(max_length=255, blank=True)
    
    connected_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_social_accounts'
        verbose_name = 'User Social Account'
        verbose_name_plural = 'User Social Accounts'
        unique_together = ['user', 'platform', 'platform_user_id']
        indexes = [
            models.Index(fields=['user', 'platform']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.platform.display_name} ({self.platform_username})"
    
    def is_token_expired(self):
        """Check if the access token is expired"""
        if not self.token_expires_at:
            return False
        return timezone.now() >= self.token_expires_at
    
    def encrypt_token(self, token):
        """Encrypt a token for secure storage"""
        if not token:
            return ''
        
        # For development, store tokens in plaintext (NOT FOR PRODUCTION)
        return token
    
    def decrypt_token(self, encrypted_token):
        """Decrypt a stored token"""
        if not encrypted_token:
            return ''
        
        # For development, tokens are stored in plaintext (NOT FOR PRODUCTION)
        return encrypted_token
    
    def save(self, *args, **kwargs):
        # Update status based on token expiry
        if self.is_token_expired() and self.status == 'connected':
            self.status = 'expired'
        
        super().save(*args, **kwargs)


class SocialPostTemplate(models.Model):
    """Model to store platform-specific post templates"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_templates')
    platform = models.ForeignKey(SocialPlatform, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    template_content = models.JSONField(help_text='Platform-specific template structure')
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_post_templates'
        verbose_name = 'Social Post Template'
        verbose_name_plural = 'Social Post Templates'
        unique_together = ['user', 'platform', 'name']
    
    def __str__(self):
        return f"{self.user.email} - {self.platform.display_name} - {self.name}"


class SocialAccountAnalytics(models.Model):
    """Model to store analytics data for connected social media accounts"""
    
    account = models.OneToOneField(UserSocialAccount, on_delete=models.CASCADE, related_name='analytics')
    
    # YouTube specific analytics
    subscriber_count = models.BigIntegerField(null=True, blank=True)
    video_count = models.IntegerField(null=True, blank=True)
    view_count = models.BigIntegerField(null=True, blank=True)
    
    # Instagram specific analytics
    follower_count = models.BigIntegerField(null=True, blank=True)
    following_count = models.BigIntegerField(null=True, blank=True)
    media_count = models.IntegerField(null=True, blank=True)
    
    # LinkedIn specific analytics
    connection_count = models.IntegerField(null=True, blank=True)
    
    # Twitter specific analytics
    tweet_count = models.IntegerField(null=True, blank=True)
    
    # TikTok specific analytics
    likes_count = models.BigIntegerField(null=True, blank=True)
    
    # Common analytics
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    last_post_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'social_account_analytics'
        verbose_name = 'Social Account Analytics'
        verbose_name_plural = 'Social Account Analytics'
    
    def __str__(self):
        return f"{self.account.platform.display_name} Analytics - {self.account.platform_username}"