from django.urls import path
from . import views

app_name = 'social_platforms'

urlpatterns = [
    # Platform management
    path('platforms/', views.get_available_platforms, name='available_platforms'),
    path('accounts/', views.get_user_connected_accounts, name='connected_accounts'),
    
    # OAuth flow
    path('connect/<str:platform_name>/', views.initiate_oauth, name='initiate_oauth'),
    path('callback/<str:platform_name>/', views.handle_oauth_callback, name='oauth_callback'),
    
    # Account management
    path('disconnect/<int:account_id>/', views.disconnect_account, name='disconnect_account'),
    
    # Analytics endpoints
    path('analytics/', views.get_account_analytics, name='get_all_analytics'),
    path('analytics/<int:account_id>/', views.get_account_analytics, name='get_account_analytics'),
    path('analytics/<int:account_id>/refresh/', views.refresh_account_analytics, name='refresh_analytics'),
    path('analytics/<int:account_id>/detailed/', views.get_detailed_analytics, name='detailed_analytics'),
    path('debug/<int:account_id>/', views.debug_account, name='debug_account'),
    
    # Video management endpoints
    path('videos/<int:account_id>/', views.get_videos, name='get_videos'),
    path('videos/<int:account_id>/<str:video_id>/', views.get_video_details, name='get_video_details'),
    path('videos/<int:account_id>/<str:video_id>/update/', views.update_video, name='update_video'),
    # YouTube platform settings (not video-specific)
    path('youtube/<int:account_id>/categories/', views.get_video_categories, name='get_video_categories'),
    path('youtube/<int:account_id>/languages/', views.get_supported_languages, name='get_supported_languages'),
]