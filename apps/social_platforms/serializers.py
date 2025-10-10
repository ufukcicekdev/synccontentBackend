from rest_framework import serializers
from .models import (
    SocialPlatform, UserSocialAccount, LinkedInOrganization, LinkedInPost,
    YouTubeAnalytics, LinkedInAnalytics, InstagramAnalytics, TwitterAnalytics, TikTokAnalytics, InstagramMedia
)


class SocialPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialPlatform
        fields = [
            'id', 'name', 'display_name', 'icon_class', 'color_class', 
            'is_active'
        ]


class UserSocialAccountSerializer(serializers.ModelSerializer):
    platform = SocialPlatformSerializer(read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSocialAccount
        fields = [
            'id', 'platform', 'platform_user_id', 'platform_username',
            'platform_display_name', 'profile_picture_url', 'status',
            'is_expired', 'connected_at', 'last_used_at'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_token_expired()


class SocialAccountConnectionSerializer(serializers.Serializer):
    platform_name = serializers.CharField(max_length=50)
    code = serializers.CharField()
    state = serializers.CharField()


class LinkedInOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInOrganization
        fields = [
            'id', 'organization_id', 'name', 'vanity_name', 'description',
            'website_url', 'industry', 'company_size', 'logo_url', 'cover_photo_url',
            'follower_count', 'employee_count_range', 'user_role', 'is_admin',
            'can_post', 'created_at', 'updated_at'
        ]


class LinkedInPostSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    total_engagement = serializers.ReadOnlyField()
    engagement_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = LinkedInPost
        fields = [
            'id', 'post_id', 'urn', 'post_type', 'state', 'text_content',
            'media_urls', 'article_url', 'article_title', 'article_description',
            'like_count', 'comment_count', 'share_count', 'view_count', 'click_count',
            'total_engagement', 'engagement_rate', 'organization_name',
            'published_at', 'last_modified_at', 'created_at', 'updated_at'
        ]


class YouTubeAnalyticsSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='account.platform.name', read_only=True)
    platform_display_name = serializers.CharField(source='account.platform.display_name', read_only=True)
    platform_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = YouTubeAnalytics
        fields = '__all__'


class LinkedInAnalyticsSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='account.platform.name', read_only=True)
    platform_display_name = serializers.CharField(source='account.platform.display_name', read_only=True)
    platform_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    recent_engagement_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = LinkedInAnalytics
        fields = '__all__'


class InstagramAnalyticsSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='account.platform.name', read_only=True)
    platform_display_name = serializers.CharField(source='account.platform.display_name', read_only=True)
    platform_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = InstagramAnalytics
        fields = '__all__'


class TwitterAnalyticsSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='account.platform.name', read_only=True)
    platform_display_name = serializers.CharField(source='account.platform.display_name', read_only=True)
    platform_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = TwitterAnalytics
        fields = '__all__'


class TikTokAnalyticsSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='account.platform.name', read_only=True)
    platform_display_name = serializers.CharField(source='account.platform.display_name', read_only=True)
    platform_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = TikTokAnalytics
        fields = '__all__'


class InstagramMediaSerializer(serializers.ModelSerializer):
    account_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = InstagramMedia
        fields = [
            'id', 'account_id', 'account_username', 'media_id', 'media_type',
            'media_url', 'permalink', 'caption', 'like_count', 'comments_count',
            'timestamp', 'created_at', 'updated_at', 'total_engagement', 'engagement_rate'
        ]
        read_only_fields = ['id', 'account_id', 'account_username', 'created_at', 'updated_at',
                           'total_engagement', 'engagement_rate']


# Unified serializer for different platform analytics
class UnifiedAnalyticsSerializer(serializers.Serializer):
    """Unified serializer to handle different platform analytics in a consistent format"""
    
    platform_name = serializers.CharField()
    platform_display_name = serializers.CharField()
    platform_username = serializers.CharField()
    account_id = serializers.IntegerField()
    last_updated = serializers.DateTimeField()
    
    # Common fields that might exist across platforms
    follower_count = serializers.IntegerField(required=False)
    following_count = serializers.IntegerField(required=False)
    engagement_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    
    # Platform-specific fields (optional)
    subscriber_count = serializers.IntegerField(required=False)  # YouTube
    video_count = serializers.IntegerField(required=False)  # YouTube, TikTok
    total_view_count = serializers.IntegerField(required=False)  # YouTube
    
    connection_count = serializers.IntegerField(required=False)  # LinkedIn
    post_count = serializers.IntegerField(required=False)  # LinkedIn
    profile_views = serializers.IntegerField(required=False)  # LinkedIn
    total_organizations = serializers.IntegerField(required=False)  # LinkedIn
    
    media_count = serializers.IntegerField(required=False)  # Instagram
    tweet_count = serializers.IntegerField(required=False)  # Twitter
    
    def to_representation(self, instance):
        """Convert platform-specific analytics to unified format"""
        data = {
            'platform_name': instance.account.platform.name,
            'platform_display_name': instance.account.platform.display_name,
            'platform_username': instance.account.platform_username,
            'account_id': instance.account.id,
            'last_updated': instance.last_updated,
        }
        
        # Add platform-specific fields based on instance type
        if isinstance(instance, YouTubeAnalytics):
            data.update({
                'subscriber_count': instance.subscriber_count,
                'video_count': instance.video_count,
                'total_view_count': instance.total_view_count,
                'engagement_rate': instance.engagement_rate,
            })
        elif isinstance(instance, LinkedInAnalytics):
            data.update({
                'connection_count': instance.connection_count,
                'follower_count': instance.follower_count,
                'post_count': instance.post_count,
                'profile_views': instance.profile_views,
                'total_organizations': instance.total_organizations,
                'engagement_rate': instance.engagement_rate,
            })
        elif isinstance(instance, InstagramAnalytics):
            data.update({
                'follower_count': instance.follower_count,
                'following_count': instance.following_count,
                'media_count': instance.media_count,
                'engagement_rate': instance.engagement_rate,
            })
        elif isinstance(instance, TwitterAnalytics):
            data.update({
                'follower_count': instance.follower_count,
                'following_count': instance.following_count,
                'tweet_count': instance.tweet_count,
                'engagement_rate': instance.engagement_rate,
            })
        elif isinstance(instance, TikTokAnalytics):
            data.update({
                'follower_count': instance.follower_count,
                'following_count': instance.following_count,
                'video_count': instance.video_count,
                'engagement_rate': instance.engagement_rate,
            })
        
        return data