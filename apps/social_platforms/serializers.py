from rest_framework import serializers
from .models import SocialPlatform, UserSocialAccount, SocialAccountAnalytics


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


class SocialAccountAnalyticsSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='account.platform.name', read_only=True)
    platform_display_name = serializers.CharField(source='account.platform.display_name', read_only=True)
    platform_username = serializers.CharField(source='account.platform_username', read_only=True)
    account_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = SocialAccountAnalytics
        fields = [
            'id', 'account_id', 'platform_name', 'platform_display_name', 'platform_username',
            'subscriber_count', 'video_count', 'view_count', 'follower_count',
            'following_count', 'media_count', 'connection_count', 'tweet_count',
            'likes_count', 'engagement_rate', 'last_post_date', 'last_updated'
        ]