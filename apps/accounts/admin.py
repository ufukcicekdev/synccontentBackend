from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile


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