from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, SystemLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'subscription_tier', 'is_verified', 'is_staff', 'created_at')
    list_filter = ('subscription_tier', 'is_verified', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('email', 'full_name', 'username')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'full_name', 'profile_picture')}),
        ('Subscription', {'fields': ('subscription_tier', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'full_name', 'password1', 'password2', 'subscription_tier'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'timezone', 'language')
    list_filter = ('timezone', 'language', 'marketing_emails')
    search_fields = ('user__email', 'user__full_name', 'company_name')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Company Info', {'fields': ('company_name', 'website_url', 'bio')}),
        ('Preferences', {'fields': ('timezone', 'language', 'marketing_emails')}),
    )


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level_colored', 'logger_name', 'user', 'created', 'request_path', 'truncated_message')
    list_filter = ('level', 'logger_name', 'created', 'user')
    search_fields = ('message', 'logger_name', 'request_path', 'user__email')
    readonly_fields = ('level', 'logger_name', 'message', 'pathname', 'funcName', 'lineno', 'created', 'user', 'request_path', 'request_method', 'ip_address', 'user_agent', 'extra_data')
    ordering = ('-created',)
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Log Info', {
            'fields': ('level', 'logger_name', 'message', 'created')
        }),
        ('Code Location', {
            'fields': ('pathname', 'funcName', 'lineno'),
            'classes': ('collapse',),
        }),
        ('Request Info', {
            'fields': ('user', 'request_path', 'request_method', 'ip_address', 'user_agent'),
            'classes': ('collapse',),
        }),
        ('Extra Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def level_colored(self, obj):
        colors = {
            'DEBUG': '#6c757d',
            'INFO': '#007bff',
            'WARNING': '#ffc107',
            'ERROR': '#dc3545',
            'CRITICAL': '#6f42c1',
        }
        color = colors.get(obj.level, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.level
        )
    level_colored.short_description = 'Level'
    
    def truncated_message(self, obj):
        return (obj.message[:100] + '...') if len(obj.message) > 100 else obj.message
    truncated_message.short_description = 'Message'