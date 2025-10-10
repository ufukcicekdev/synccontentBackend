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


class LinkedInOrganization(models.Model):
    """Model to store LinkedIn organization/company page information"""
    
    account = models.ForeignKey(UserSocialAccount, on_delete=models.CASCADE, related_name='linkedin_organizations')
    organization_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    vanity_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True)
    industry = models.CharField(max_length=255, blank=True)
    company_size = models.CharField(max_length=100, blank=True)
    logo_url = models.URLField(blank=True)
    cover_photo_url = models.URLField(blank=True)
    follower_count = models.BigIntegerField(null=True, blank=True)
    employee_count_range = models.CharField(max_length=100, blank=True)
    
    # User's role in the organization
    user_role = models.CharField(max_length=100, blank=True)
    is_admin = models.BooleanField(default=False)
    can_post = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'linkedin_organizations'
        verbose_name = 'LinkedIn Organization'
        verbose_name_plural = 'LinkedIn Organizations'
        unique_together = ['account', 'organization_id']
    
    def __str__(self):
        return f"{self.name} - {self.account.platform_username}"


class LinkedInPost(models.Model):
    """Model to store LinkedIn posts/activities"""
    
    POST_TYPE_CHOICES = [
        ('ARTICLE', 'Article'),
        ('RICH_MEDIA', 'Rich Media'),
        ('UGC_POST', 'User Generated Content'),
        ('VIDEO', 'Video'),
        ('IMAGE', 'Image'),
        ('TEXT', 'Text Only'),
    ]
    
    POST_STATE_CHOICES = [
        ('PUBLISHED', 'Published'),
        ('DRAFT', 'Draft'),
        ('PROCESSING', 'Processing'),
        ('READY', 'Ready'),
    ]
    
    account = models.ForeignKey(UserSocialAccount, on_delete=models.CASCADE, related_name='linkedin_posts')
    organization = models.ForeignKey(LinkedInOrganization, on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    
    # LinkedIn API data
    post_id = models.CharField(max_length=255, unique=True)
    urn = models.CharField(max_length=500, blank=True)  # LinkedIn URN
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='UGC_POST')
    state = models.CharField(max_length=20, choices=POST_STATE_CHOICES, default='PUBLISHED')
    
    # Content
    text_content = models.TextField(blank=True)
    media_urls = models.JSONField(default=list, help_text='List of media URLs')
    article_url = models.URLField(blank=True)
    article_title = models.CharField(max_length=500, blank=True)
    article_description = models.TextField(blank=True)
    
    # Analytics
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    # Metadata
    published_at = models.DateTimeField(null=True, blank=True)
    last_modified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'linkedin_posts'
        verbose_name = 'LinkedIn Post'
        verbose_name_plural = 'LinkedIn Posts'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['account', 'published_at']),
            models.Index(fields=['organization', 'published_at']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f"LinkedIn Post {self.post_id} - {self.account.platform_username}"
    
    @property
    def total_engagement(self):
        return self.like_count + self.comment_count + self.share_count
    
    @property
    def engagement_rate(self):
        if self.view_count > 0:
            return (self.total_engagement / self.view_count) * 100
        return 0


class YouTubeAnalytics(models.Model):
    """Dedicated model for YouTube channel analytics"""
    
    account = models.OneToOneField(UserSocialAccount, on_delete=models.CASCADE, related_name='youtube_analytics')
    
    # Channel metrics
    subscriber_count = models.BigIntegerField(default=0)
    video_count = models.IntegerField(default=0)
    total_view_count = models.BigIntegerField(default=0)
    total_like_count = models.BigIntegerField(default=0)
    total_comment_count = models.BigIntegerField(default=0)
    
    # Channel info
    channel_title = models.CharField(max_length=255, blank=True)
    channel_description = models.TextField(blank=True)
    channel_thumbnail_url = models.URLField(blank=True)
    channel_country = models.CharField(max_length=10, blank=True)
    channel_created_at = models.DateTimeField(null=True, blank=True)
    
    # Growth metrics (30 days)
    subscriber_growth_30d = models.IntegerField(default=0)
    view_growth_30d = models.BigIntegerField(default=0)
    video_growth_30d = models.IntegerField(default=0)
    
    # Engagement metrics
    average_views_per_video = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_likes_per_video = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_comments_per_video = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Performance metrics
    most_viewed_video_id = models.CharField(max_length=50, blank=True)
    most_viewed_video_views = models.BigIntegerField(default=0)
    most_liked_video_id = models.CharField(max_length=50, blank=True)
    most_liked_video_likes = models.BigIntegerField(default=0)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'youtube_analytics'
        verbose_name = 'YouTube Analytics'
        verbose_name_plural = 'YouTube Analytics'
    
    def __str__(self):
        return f"YouTube Analytics - {self.account.platform_username}"


class LinkedInAnalytics(models.Model):
    """Dedicated model for LinkedIn profile analytics"""
    
    account = models.OneToOneField(UserSocialAccount, on_delete=models.CASCADE, related_name='linkedin_analytics')
    
    # Profile metrics
    connection_count = models.IntegerField(default=0)
    follower_count = models.BigIntegerField(default=0)
    post_count = models.IntegerField(default=0)
    article_count = models.IntegerField(default=0)
    
    # Visibility metrics
    profile_views = models.IntegerField(default=0)
    search_appearances = models.IntegerField(default=0)
    profile_views_30d = models.IntegerField(default=0)
    search_appearances_30d = models.IntegerField(default=0)
    
    # Organization metrics
    total_organizations = models.IntegerField(default=0)
    managed_pages = models.IntegerField(default=0)
    organization_follower_count = models.BigIntegerField(default=0)
    
    # Content metrics
    total_post_views = models.BigIntegerField(default=0)
    total_post_likes = models.BigIntegerField(default=0)
    total_post_comments = models.BigIntegerField(default=0)
    total_post_shares = models.BigIntegerField(default=0)
    
    # Recent activity (30 days)
    recent_posts_count = models.IntegerField(default=0)
    recent_total_likes = models.BigIntegerField(default=0)
    recent_total_comments = models.BigIntegerField(default=0)
    recent_total_shares = models.BigIntegerField(default=0)
    recent_total_views = models.BigIntegerField(default=0)
    
    # Engagement metrics
    average_post_engagement = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    connection_growth_30d = models.IntegerField(default=0)
    
    # Profile information
    headline = models.CharField(max_length=500, blank=True)
    summary = models.TextField(blank=True)
    industry = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'linkedin_analytics'
        verbose_name = 'LinkedIn Analytics'
        verbose_name_plural = 'LinkedIn Analytics'
    
    def __str__(self):
        return f"LinkedIn Analytics - {self.account.platform_username}"
    
    @property
    def recent_engagement_rate(self):
        """Calculate engagement rate for recent posts"""
        if self.recent_total_views > 0:
            total_engagement = self.recent_total_likes + self.recent_total_comments + self.recent_total_shares
            return (total_engagement / self.recent_total_views) * 100
        return 0


class InstagramAnalytics(models.Model):
    """Dedicated model for Instagram account analytics"""
    
    account = models.OneToOneField(UserSocialAccount, on_delete=models.CASCADE, related_name='instagram_analytics')
    
    # Account metrics
    follower_count = models.BigIntegerField(default=0)
    following_count = models.BigIntegerField(default=0)
    media_count = models.IntegerField(default=0)
    
    # Account type and verification
    account_type = models.CharField(max_length=20, blank=True)  # PERSONAL, BUSINESS, CREATOR
    is_verified = models.BooleanField(default=False)
    is_business_account = models.BooleanField(default=False)
    
    # Content metrics
    total_likes = models.BigIntegerField(default=0)
    total_comments = models.BigIntegerField(default=0)
    total_video_views = models.BigIntegerField(default=0)
    total_reach = models.BigIntegerField(default=0)
    total_impressions = models.BigIntegerField(default=0)
    
    # Growth metrics (30 days)
    follower_growth_30d = models.IntegerField(default=0)
    media_growth_30d = models.IntegerField(default=0)
    
    # Engagement metrics
    average_likes_per_post = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_comments_per_post = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Recent activity (30 days)
    recent_posts_count = models.IntegerField(default=0)
    recent_total_likes = models.BigIntegerField(default=0)
    recent_total_comments = models.BigIntegerField(default=0)
    recent_total_reach = models.BigIntegerField(default=0)
    recent_total_impressions = models.BigIntegerField(default=0)
    
    # Profile information
    biography = models.TextField(blank=True)
    website = models.URLField(blank=True)
    profile_picture_url = models.URLField(blank=True)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'instagram_analytics'
        verbose_name = 'Instagram Analytics'
        verbose_name_plural = 'Instagram Analytics'
    
    def __str__(self):
        return f"Instagram Analytics - {self.account.platform_username}"


class InstagramMedia(models.Model):
    """Model to store Instagram media posts/content"""
    
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('CAROUSEL_ALBUM', 'Carousel Album'),
    ]
    
    account = models.ForeignKey(UserSocialAccount, on_delete=models.CASCADE, related_name='instagram_media')
    
    # Instagram API data
    media_id = models.CharField(max_length=255, unique=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='IMAGE')
    media_url = models.URLField(blank=True)
    permalink = models.URLField(blank=True)
    
    # Content
    caption = models.TextField(blank=True)
    
    # Analytics
    like_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    
    # Metadata
    timestamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'instagram_media'
        verbose_name = 'Instagram Media'
        verbose_name_plural = 'Instagram Media'
        ordering = ['-timestamp', '-created_at']
        indexes = [
            models.Index(fields=['account', 'timestamp']),
            models.Index(fields=['media_type']),
        ]
    
    def __str__(self):
        return f"Instagram Media {self.media_id} - {self.account.platform_username}"
    
    @property
    def total_engagement(self):
        return self.like_count + self.comments_count
    
    @property
    def engagement_rate(self):
        # This would need follower count context, but we can calculate a basic rate
        if hasattr(self.account, 'instagram_analytics') and self.account.instagram_analytics.follower_count:
            return (self.total_engagement / self.account.instagram_analytics.follower_count) * 100
        return 0


class TwitterAnalytics(models.Model):
    """Dedicated model for Twitter/X account analytics"""
    
    account = models.OneToOneField(UserSocialAccount, on_delete=models.CASCADE, related_name='twitter_analytics')
    
    # Account metrics
    follower_count = models.BigIntegerField(default=0)
    following_count = models.BigIntegerField(default=0)
    tweet_count = models.IntegerField(default=0)
    listed_count = models.IntegerField(default=0)
    
    # Account information
    is_verified = models.BooleanField(default=False)
    is_protected = models.BooleanField(default=False)
    account_created_at = models.DateTimeField(null=True, blank=True)
    
    # Content metrics
    total_likes = models.BigIntegerField(default=0)
    total_retweets = models.BigIntegerField(default=0)
    total_replies = models.BigIntegerField(default=0)
    total_quotes = models.BigIntegerField(default=0)
    
    # Growth metrics (30 days)
    follower_growth_30d = models.IntegerField(default=0)
    tweet_growth_30d = models.IntegerField(default=0)
    
    # Engagement metrics
    average_likes_per_tweet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_retweets_per_tweet = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Recent activity (30 days)
    recent_tweets_count = models.IntegerField(default=0)
    recent_total_likes = models.BigIntegerField(default=0)
    recent_total_retweets = models.BigIntegerField(default=0)
    recent_total_replies = models.BigIntegerField(default=0)
    
    # Profile information
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    profile_image_url = models.URLField(blank=True)
    profile_banner_url = models.URLField(blank=True)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'twitter_analytics'
        verbose_name = 'Twitter Analytics'
        verbose_name_plural = 'Twitter Analytics'
    
    def __str__(self):
        return f"Twitter Analytics - {self.account.platform_username}"


class TikTokAnalytics(models.Model):
    """Dedicated model for TikTok account analytics"""
    
    account = models.OneToOneField(UserSocialAccount, on_delete=models.CASCADE, related_name='tiktok_analytics')
    
    # Account metrics
    follower_count = models.BigIntegerField(default=0)
    following_count = models.BigIntegerField(default=0)
    video_count = models.IntegerField(default=0)
    
    # Account information
    is_verified = models.BooleanField(default=False)
    avatar_url = models.URLField(blank=True)
    
    # Content metrics
    total_likes = models.BigIntegerField(default=0)
    total_views = models.BigIntegerField(default=0)
    total_shares = models.BigIntegerField(default=0)
    total_comments = models.BigIntegerField(default=0)
    
    # Growth metrics (30 days)
    follower_growth_30d = models.IntegerField(default=0)
    video_growth_30d = models.IntegerField(default=0)
    
    # Engagement metrics
    average_likes_per_video = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_views_per_video = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Recent activity (30 days)
    recent_videos_count = models.IntegerField(default=0)
    recent_total_likes = models.BigIntegerField(default=0)
    recent_total_views = models.BigIntegerField(default=0)
    recent_total_shares = models.BigIntegerField(default=0)
    recent_total_comments = models.BigIntegerField(default=0)
    
    # Profile information
    display_name = models.CharField(max_length=255, blank=True)
    bio_description = models.TextField(blank=True)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tiktok_analytics'
        verbose_name = 'TikTok Analytics'
        verbose_name_plural = 'TikTok Analytics'
    
    def __str__(self):
        return f"TikTok Analytics - {self.account.platform_username}"