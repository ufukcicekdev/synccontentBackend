from django.contrib import admin
from .models import SocialPlatform, UserSocialAccount, SocialPostTemplate


@admin.register(SocialPlatform)
class SocialPlatformAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'is_active', 'created_at')
    list_filter = ('is_active', 'name')
    search_fields = ('name', 'display_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name', 'is_active')
        }),
        ('Styling', {
            'fields': ('icon_class', 'color_class')
        }),
        ('OAuth Configuration', {
            'fields': (
                'oauth_client_id', 'oauth_client_secret', 
                'oauth_authorization_url', 'oauth_token_url', 'oauth_scope'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserSocialAccount)
class UserSocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'platform_username', 'status', 'connected_at')
    list_filter = ('platform', 'status', 'connected_at')
    search_fields = ('user__email', 'platform_username', 'platform_display_name')
    readonly_fields = ('connected_at', 'updated_at', 'access_token', 'refresh_token')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'platform', 'status')
        }),
        ('Platform Data', {
            'fields': (
                'platform_user_id', 'platform_username', 
                'platform_display_name', 'profile_picture_url'
            )
        }),
        ('OAuth Data', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('permissions', 'oauth_state', 'oauth_code_verifier'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('connected_at', 'last_used_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'platform')


@admin.register(SocialPostTemplate)
class SocialPostTemplateAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'name', 'is_default', 'created_at')
    list_filter = ('platform', 'is_default', 'created_at')
    search_fields = ('user__email', 'name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Template Information', {
            'fields': ('user', 'platform', 'name', 'is_default')
        }),
        ('Template Content', {
            'fields': ('template_content',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )