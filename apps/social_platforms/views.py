from typing import Any
from rest_framework import status
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
import requests
import secrets
import string
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

from .models import SocialPlatform, UserSocialAccount, LinkedInOrganization, LinkedInPost, YouTubeAnalytics, LinkedInAnalytics, InstagramAnalytics, TwitterAnalytics, TikTokAnalytics, InstagramMedia
from .serializers import (
    SocialPlatformSerializer, UserSocialAccountSerializer, LinkedInOrganizationSerializer, LinkedInPostSerializer,
    YouTubeAnalyticsSerializer, LinkedInAnalyticsSerializer, InstagramAnalyticsSerializer, 
    TwitterAnalyticsSerializer, TikTokAnalyticsSerializer, UnifiedAnalyticsSerializer, InstagramMediaSerializer
)
from .services import SocialAnalyticsService, YouTubeAnalyticsService, InstagramAnalyticsService


def get_analytics_for_account(account):
    """Helper function to get analytics data for any platform account"""
    platform = account.platform.name
    
    # Try to get platform-specific analytics
    try:
        if platform == 'youtube':
            analytics = YouTubeAnalytics.objects.get(account=account)
            serializer = YouTubeAnalyticsSerializer(analytics)
        elif platform == 'linkedin':
            analytics = LinkedInAnalytics.objects.get(account=account)
            serializer = LinkedInAnalyticsSerializer(analytics)
        elif platform == 'instagram':
            analytics = InstagramAnalytics.objects.get(account=account)
            serializer = InstagramAnalyticsSerializer(analytics)
        elif platform == 'twitter':
            analytics = TwitterAnalytics.objects.get(account=account)
            serializer = TwitterAnalyticsSerializer(analytics)
        elif platform == 'tiktok':
            analytics = TikTokAnalytics.objects.get(account=account)
            serializer = TikTokAnalyticsSerializer(analytics)
        else:
            raise Exception(f"Unsupported platform: {platform}")
        
        # Use UnifiedAnalyticsSerializer to create consistent response
        unified_serializer = UnifiedAnalyticsSerializer(analytics)
        return unified_serializer.data
        
    except (YouTubeAnalytics.DoesNotExist, LinkedInAnalytics.DoesNotExist, 
            InstagramAnalytics.DoesNotExist, TwitterAnalytics.DoesNotExist,
            TikTokAnalytics.DoesNotExist):
        # Return basic account info if no analytics exist yet
        return {
            'account_id': account.id,
            'platform_name': account.platform.name,
            'platform_display_name': account.platform.display_name,
            'platform_username': account.platform_username,
            'last_updated': account.updated_at.isoformat(),
            'message': 'Analytics data not available yet'
        }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_platforms(request):
    """Get list of available social media platforms"""
    platforms = SocialPlatform.objects.filter(is_active=True)
    serializer = SocialPlatformSerializer(platforms, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_connected_accounts(request):
    """Get user's connected social media accounts"""
    accounts = UserSocialAccount.objects.filter(user=request.user).select_related('platform')
    serializer = UserSocialAccountSerializer(accounts, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_oauth(request, platform_name):
    """Initiate OAuth flow for a social media platform"""
    try:
        platform = SocialPlatform.objects.get(name=platform_name, is_active=True)
    except SocialPlatform.DoesNotExist:
        return Response({
            'error': 'Platform not found or not supported'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if OAuth credentials are configured
    if not platform.oauth_client_id or not platform.oauth_client_secret:
        error_messages = {
            'instagram': 'Instagram OAuth is not configured. Please set up OAuth credentials in Facebook Developers Console.',
            'youtube': 'YouTube OAuth is not configured. Please set up OAuth credentials in Google Cloud Console.',
            'linkedin': 'LinkedIn OAuth is not configured. Please set up OAuth credentials in LinkedIn Developer Portal.',
            'twitter': 'Twitter OAuth is not configured. Please set up OAuth credentials in Twitter Developer Portal.',
            'tiktok': 'TikTok OAuth is not configured. Please set up OAuth credentials in TikTok Developers Portal.'
        }
        return Response({
            'error': error_messages.get(platform_name, f'{platform.display_name} OAuth is not configured. Please contact administrator.'),
            'details': f'Missing OAuth credentials for {platform_name}. Client ID and Client Secret are required.',
            'setup_required': True,
            'platform': platform_name
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    # Generate state for CSRF protection
    state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    # Store state in session or cache (for now using a simple approach)
    request.session[f'oauth_state_{platform_name}'] = state
    
    # Build OAuth authorization URL
    if platform_name == 'linkedin':
        # Special handling for LinkedIn to ensure correct parameter order matching LinkedIn's documentation
        authorization_url = (
            f"{platform.oauth_authorization_url}?"
            f"response_type=code&"
            f"client_id={platform.oauth_client_id}&"
            f"redirect_uri={settings.FRONTEND_URL}/auth/callback/{platform_name}&"
            f"state={state}&"
            f"scope={platform.oauth_scope}"
        )
    else:
        oauth_params = {
            'client_id': platform.oauth_client_id,
            'redirect_uri': f"{settings.FRONTEND_URL}/auth/callback/{platform_name}",
            'scope': platform.oauth_scope,
            'state': state,
            'response_type': 'code',
        }
        
        # Platform-specific parameters
        if platform_name == 'instagram':
            oauth_params['response_type'] = 'code'
        elif platform_name == 'youtube':
            oauth_params['access_type'] = 'offline'
            oauth_params['prompt'] = 'consent'
        elif platform_name == 'linkedin':
            oauth_params['response_type'] = 'code'
        
        authorization_url = f"{platform.oauth_authorization_url}?{urlencode(oauth_params)}"
    
    return Response({
        'authorization_url': authorization_url,
        'state': state
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_oauth_callback(request, platform_name):
    """Handle OAuth callback and exchange code for tokens"""
    code = request.data.get('code')
    state = request.data.get('state')
    
    if not code:
        return Response({
            'error': 'Authorization code is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify state to prevent CSRF attacks - temporarily disabled for debugging
    stored_state = request.session.get(f'oauth_state_{platform_name}')
    # if not stored_state or stored_state != state:
    #     return Response({
    #         'error': 'Invalid state parameter'
    #     }, status=status.HTTP_400_BAD_REQUEST)
    
    # Temporary logging
    print(f"DEBUG: OAuth callback for {platform_name}")
    print(f"DEBUG: Code present: {'yes' if code else 'no'}")
    print(f"DEBUG: State received: {state}")
    print(f"DEBUG: State stored: {stored_state}")
    
    try:
        platform = SocialPlatform.objects.get(name=platform_name, is_active=True)
    except SocialPlatform.DoesNotExist:
        return Response({
            'error': 'Platform not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Exchange code for access token
    if platform_name == 'linkedin':
        # Special handling for LinkedIn token exchange
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f"{settings.FRONTEND_URL}/auth/callback/{platform_name}",
            'client_id': platform.oauth_client_id,
            'client_secret': platform.oauth_client_secret,
        }
    else:
        token_data: dict[str, Any] = {
            'client_id': platform.oauth_client_id,
            'client_secret': platform.oauth_client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': f"{settings.FRONTEND_URL}/auth/callback/{platform_name}",
        }
    
    try:
        token_response = requests.post(platform.oauth_token_url, data=token_data)
        print(f"DEBUG: Token response status: {token_response.status_code}")
        print(f"DEBUG: Token response text: {token_response.text[:500]}")
        
        token_response.raise_for_status()
        tokens = token_response.json()
        
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token', '')
        
        print(f"DEBUG: Access token obtained: {'yes' if access_token else 'no'}")
        
        if not access_token:
            return Response({
                'error': 'Failed to obtain access token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user info from the platform
        user_info = get_platform_user_info(platform_name, access_token)
        print(f"DEBUG: User info obtained: {user_info}")
        
        if not user_info:
            return Response({
                'error': 'Failed to get user information from platform'
            }, status=status.HTTP_400_BAD_REQUEST)
        print("-------------",platform)
        # Create or update social account
        social_account, created = UserSocialAccount.objects.update_or_create(
            user=request.user,
            platform=platform,
            platform_user_id=user_info['id'],
            defaults={
                'platform_username': user_info.get('username', ''),
                'platform_display_name': user_info.get('display_name', ''),
                'profile_picture_url': user_info.get('profile_picture', ''),
                'access_token': access_token,  # Store in plaintext for development
                'refresh_token': refresh_token,
                'status': 'connected',
                'permissions': user_info.get('permissions', {}),
            }
        )
        
        # Automatically fetch analytics after successful connection
        try:
            from .services import SocialAnalyticsService
            print(f"DEBUG: Triggering analytics fetch for {platform_name} account {social_account.id}")
            analytics_result = SocialAnalyticsService.update_account_analytics(social_account)
            print(f"DEBUG: Analytics fetch result: {'success' if analytics_result else 'failed'}")
        except Exception as analytics_error:
            print(f"DEBUG: Analytics fetch error: {analytics_error}")
            # Don't fail the connection if analytics fetch fails
            pass
        
        # Clean up session
        if f'oauth_state_{platform_name}' in request.session:
            del request.session[f'oauth_state_{platform_name}']
        
        serializer = UserSocialAccountSerializer(social_account)
        return Response({
            'success': True,
            'account': serializer.data,
            'created': created
        })
        
    except requests.RequestException as e:
        return Response({
            'error': f'Failed to exchange code for token: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Unexpected error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def disconnect_account(request, account_id):
    """Disconnect a social media account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        account.delete()
        
        return Response({
            'success': True,
            'message': 'Account disconnected successfully'
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)


def get_platform_user_info(platform_name, access_token):
    """Get user information from social media platform"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        if platform_name == 'instagram':
            response = requests.get('https://graph.instagram.com/me?fields=id,username,media_count', headers=headers)
        elif platform_name == 'youtube':
            response = requests.get('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true', headers=headers)
        elif platform_name == 'linkedin':
            # Updated LinkedIn API endpoint with proper fields
            # Using the newer userinfo endpoint that supports OpenID Connect with the openid scope
            response = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
        elif platform_name == 'twitter':
            response = requests.get('https://api.twitter.com/2/users/me', headers=headers)
        else:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        # Platform-specific data parsing
        if platform_name == 'instagram':
            return {
                'id': data.get('id'),
                'username': data.get('username'),
                'display_name': data.get('username'),
                'profile_picture': '',
                'permissions': {'media_count': data.get('media_count', 0)}
            }
        elif platform_name == 'youtube':
            if 'items' in data and len(data['items']) > 0:
                item = data['items'][0]
                snippet = item.get('snippet', {})
                return {
                    'id': item.get('id'),
                    'username': snippet.get('customUrl', ''),
                    'display_name': snippet.get('title', ''),
                    'profile_picture': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'permissions': {}
                }
        elif platform_name == 'linkedin':
            # Parse LinkedIn user data using the new userinfo endpoint
            # This endpoint is compatible with OpenID Connect and the openid scope
            first_name = data.get('given_name', '')
            last_name = data.get('family_name', '')
            display_name = f"{first_name} {last_name}".strip()
            
            # Get profile picture if available
            profile_picture = data.get('picture', '')
            
            return {
                'id': data.get('sub'),  # Using the subject identifier from OpenID Connect
                'username': display_name,
                'display_name': display_name,
                'profile_picture': profile_picture,
                'permissions': {}
            }
        elif platform_name == 'twitter':
            return {
                'id': data.get('data', {}).get('id'),
                'username': data.get('data', {}).get('username'),
                'display_name': data.get('data', {}).get('name'),
                'profile_picture': '',
                'permissions': {}
            }
        # Add other platforms as needed
        
        return None
        
    except Exception:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_account_analytics(request, account_id=None):
    """Get analytics data for connected social media accounts"""
    try:
        if account_id:
            # Get analytics for a specific account
            try:
                account = UserSocialAccount.objects.get(
                    id=account_id,
                    user=request.user
                )
            except UserSocialAccount.DoesNotExist:
                return Response({
                    'error': 'Account not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Update analytics data
            analytics_data = SocialAnalyticsService.update_account_analytics(account)
            
            # Get the analytics object based on platform
            try:
                analytics_data = get_analytics_for_account(account)
                return Response(analytics_data)
            except Exception as e:
                logger.error(f"Error getting analytics for account {account.id}: {e}")
                return Response({
                    'message': 'No analytics data available yet',
                    'platform': account.platform.name
                })
        else:
            # Get analytics for all connected accounts
            accounts = UserSocialAccount.objects.filter(
                user=request.user,
                status='connected'
            )
            
            logger.info(f"Found {accounts.count()} connected accounts for user {request.user.id}")
            
            analytics_list = []
            for account in accounts:
                logger.info(f"Processing account {account.id} - {account.platform.name}")
                try:
                    analytics_data = get_analytics_for_account(account)
                    analytics_list.append(analytics_data)
                    logger.info(f"Found existing analytics for account {account.id}")
                except Exception as e:
                    logger.info(f"No analytics found for account {account.id}, attempting to fetch...")
                    # Try to fetch analytics if not exists
                    analytics_data = SocialAnalyticsService.update_account_analytics(account)
                    if analytics_data:
                        try:
                            analytics_data = get_analytics_for_account(account)
                            analytics_list.append(analytics_data)
                            logger.info(f"Successfully fetched analytics for account {account.id}")
                        except Exception as fetch_error:
                            logger.error(f"Failed to create analytics for account {account.id}: {fetch_error}")
                            # Add placeholder data
                            analytics_list.append({
                                'account_id': account.id,
                                'platform_name': account.platform.name,
                                'platform_display_name': account.platform.display_name,
                                'platform_username': account.platform_username,
                                'message': 'Analytics data not available'
                            })
                    else:
                        logger.error(f"Failed to fetch analytics data for account {account.id}")
                        # Add placeholder data with error
                        analytics_list.append({
                            'account_id': account.id,
                            'platform_name': account.platform.name,
                            'platform_display_name': account.platform.display_name,
                            'platform_username': account.platform_username,
                            'message': 'Failed to fetch analytics data'
                        })
            
            return Response(analytics_list)
            
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return Response({
            'error': 'Failed to fetch analytics data'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_account_analytics(request, account_id):
    """Manually refresh analytics data for a specific account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Force refresh analytics
        analytics_data = SocialAnalyticsService.update_account_analytics(account)
        
        if analytics_data:
            # Get updated analytics
            try:
                analytics_data = get_analytics_for_account(account)
                return Response({
                    'message': 'Analytics updated successfully',
                    'data': analytics_data
                })
            except Exception as e:
                logger.error(f"Error getting updated analytics for account {account_id}: {e}")
                return Response({
                    'error': 'Analytics updated but failed to retrieve updated data'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'error': 'Failed to fetch analytics from platform API'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error refreshing analytics for account {account_id}: {e}")
        return Response({
            'error': 'Failed to refresh analytics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_detailed_analytics(request, account_id):
    """Get detailed analytics including recent videos/posts for a specific account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Update analytics data first
        SocialAnalyticsService.update_account_analytics(account)
        
        # Get analytics object
        try:
            analytics_data = get_analytics_for_account(account)
        except Exception as e:
            logger.error(f"Error getting analytics for account {account.id}: {e}")
            analytics_data = {
                'platform_name': account.platform.name,
                'platform_display_name': account.platform.display_name,
                'platform_username': account.platform_username,
                'account_id': account.id,
                'message': 'Analytics data not available'
            }
        
        # Fetch additional detailed data based on platform
        if account.platform.name == 'youtube':
            # Fetch recent videos
            recent_videos = YouTubeAnalyticsService.fetch_recent_videos(account)
            analytics_data['recent_videos'] = recent_videos
            
        elif account.platform.name == 'instagram':
            # Fetch recent media posts
            recent_media = InstagramAnalyticsService.fetch_recent_media(account, limit=12)
            analytics_data['recent_media'] = recent_media
        
        return Response(analytics_data)
        
    except Exception as e:
        logger.error(f"Error fetching detailed analytics for account {account_id}: {e}")
        return Response({
            'error': 'Failed to fetch detailed analytics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_account(request, account_id):
    """Debug endpoint to check account and token status"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        
        # Check token
        access_token = account.decrypt_token(account.access_token)
        
        debug_info = {
            'account_id': account.id,
            'platform': account.platform.name,
            'username': account.platform_username,
            'status': account.status,
            'has_access_token': bool(account.access_token),
            'token_length': len(account.access_token) if account.access_token else 0,
            'decrypted_token_length': len(access_token) if access_token else 0,
            'is_token_expired': account.is_token_expired(),
            'token_expires_at': account.token_expires_at,
            'connected_at': account.connected_at,
        }
        
        # Test YouTube API call
        if account.platform.name == 'youtube' and access_token:
            try:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }
                
                test_response = requests.get(
                    'https://www.googleapis.com/youtube/v3/channels',
                    headers=headers,
                    params={
                        'part': 'snippet',
                        'mine': 'true'
                    }
                )
                
                debug_info['api_test'] = {
                    'status_code': test_response.status_code,
                    'response_preview': test_response.text[:300],
                    'success': test_response.status_code == 200
                }
                
            except Exception as e:
                debug_info['api_test'] = {
                    'error': str(e)
                }
        
        return Response(debug_info)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Debug failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_videos(request, account_id):
    """Get videos for a specific YouTube account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        
        if account.platform.name != 'youtube':
            return Response({
                'error': 'This endpoint is only for YouTube accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        max_results = request.GET.get('max_results', 10)
        videos = YouTubeAnalyticsService.fetch_recent_videos(account, int(max_results))
        
        return Response(videos)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching videos for account {account_id}: {e}")
        return Response({
            'error': 'Failed to fetch videos'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_video_details(request, account_id, video_id):
    """Get detailed information about a specific video"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        
        if account.platform.name != 'youtube':
            return Response({
                'error': 'This endpoint is only for YouTube accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        video_details = YouTubeAnalyticsService.get_video_details(account, video_id)
        
        if video_details:
            return Response(video_details)
        else:
            return Response({
                'error': 'Video not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching video details {video_id}: {e}")
        return Response({
            'error': 'Failed to fetch video details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_video(request, account_id, video_id):
    """Update video metadata (title, description, category, tags)"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        
        if account.platform.name != 'youtube':
            return Response({
                'error': 'This endpoint is only for YouTube accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        video_data = request.data
        result = YouTubeAnalyticsService.update_video(account, video_id, video_data)
        
        if result:
            return Response({
                'message': 'Video updated successfully',
                'video': result
            })
        else:
            return Response({
                'error': 'Failed to update video'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating video {video_id}: {e}")
        return Response({
            'error': 'Failed to update video'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_video_categories(request, account_id):
    """Get available video categories for YouTube"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        
        if account.platform.name != 'youtube':
            return Response({
                'error': 'This endpoint is only for YouTube accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        categories = YouTubeAnalyticsService.get_video_categories(account)
        return Response(categories)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching video categories: {e}")
        return Response({
            'error': 'Failed to fetch video categories'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_supported_languages(request, account_id):
    """Get supported languages for YouTube content"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user
        )
        
        if account.platform.name != 'youtube':
            return Response({
                'error': 'This endpoint is only for YouTube accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        languages = YouTubeAnalyticsService.get_supported_languages(account)
        return Response(languages)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching supported languages: {e}")
        return Response({
            'error': 'Failed to fetch supported languages'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# LinkedIn-specific endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_linkedin_organizations(request, account_id):
    """Get LinkedIn organizations for a specific account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='linkedin'
        )
        
        organizations = LinkedInOrganization.objects.filter(account=account)
        serializer = LinkedInOrganizationSerializer(organizations, many=True)
        
        return Response({
            'organizations': serializer.data,
            'total_count': organizations.count()
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'LinkedIn account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching LinkedIn organizations: {e}")
        return Response({
            'error': 'Failed to fetch organizations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_linkedin_posts(request, account_id):
    """Get LinkedIn posts for a specific account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='linkedin'
        )
        
        # Pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Filter parameters
        post_type = request.GET.get('type')
        organization_id = request.GET.get('organization')
        
        # Build query
        posts_query = LinkedInPost.objects.filter(account=account)
        
        if post_type:
            posts_query = posts_query.filter(post_type=post_type)
        
        if organization_id:
            posts_query = posts_query.filter(organization__organization_id=organization_id)
        
        # Get total count
        total_count = posts_query.count()
        
        # Apply pagination
        posts = posts_query[offset:offset + page_size]
        
        serializer = LinkedInPostSerializer(posts, many=True)
        
        return Response({
            'posts': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'LinkedIn account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching LinkedIn posts: {e}")
        return Response({
            'error': 'Failed to fetch posts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_linkedin_post_detail(request, account_id, post_id):
    """Get detailed information about a specific LinkedIn post"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='linkedin'
        )
        
        post = LinkedInPost.objects.get(
            account=account,
            post_id=post_id
        )
        
        serializer = LinkedInPostSerializer(post)
        
        return Response(serializer.data)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'LinkedIn account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except LinkedInPost.DoesNotExist:
        return Response({
            'error': 'Post not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching LinkedIn post detail: {e}")
        return Response({
            'error': 'Failed to fetch post detail'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_linkedin_post(request, account_id, post_id):
    """Update a LinkedIn post"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='linkedin'
        )
        
        post = LinkedInPost.objects.get(
            account=account,
            post_id=post_id
        )
        
        # LinkedIn doesn't allow editing published posts via API
        # This endpoint updates our local data only
        serializer = LinkedInPostSerializer(post, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'LinkedIn account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except LinkedInPost.DoesNotExist:
        return Response({
            'error': 'Post not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating LinkedIn post: {e}")
        return Response({
            'error': 'Failed to update post'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_linkedin_post(request, account_id, post_id):
    """Delete a LinkedIn post"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='linkedin'
        )
        
        post = LinkedInPost.objects.get(
            account=account,
            post_id=post_id
        )
        
        # Try to delete from LinkedIn via API
        access_token = account.decrypt_token(account.access_token)
        if access_token:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Delete from LinkedIn
            delete_response = requests.delete(
                f'https://api.linkedin.com/v2/ugcPosts/{post.urn}',
                headers=headers
            )
            
            if delete_response.status_code not in [200, 204, 404]:
                return Response({
                    'error': 'Failed to delete post from LinkedIn',
                    'details': delete_response.text
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete from our database
        post.delete()
        
        return Response({
            'message': 'Post deleted successfully'
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'LinkedIn account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except LinkedInPost.DoesNotExist:
        return Response({
            'error': 'Post not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting LinkedIn post: {e}")
        return Response({
            'error': 'Failed to delete post'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_linkedin_post(request, account_id):
    """Create a new LinkedIn post"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='linkedin'
        )
        
        access_token = account.decrypt_token(account.access_token)
        if not access_token:
            return Response({
                'error': 'Access token not available'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Extract post data
        text_content = request.data.get('text_content', '')
        organization_id = request.data.get('organization_id')
        media_urls = request.data.get('media_urls', [])
        
        # Determine author URN
        if organization_id:
            author_urn = f'urn:li:organization:{organization_id}'
        else:
            author_urn = f'urn:li:person:{account.platform_user_id}'
        
        # Prepare post data for LinkedIn API
        post_data = {
            'author': author_urn,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {
                        'text': text_content
                    },
                    'shareMediaCategory': 'NONE'
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        }
        
        # Add media if provided
        if media_urls:
            post_data['specificContent']['com.linkedin.ugc.ShareContent']['shareMediaCategory'] = 'IMAGE'
            post_data['specificContent']['com.linkedin.ugc.ShareContent']['media'] = [
                {
                    'status': 'READY',
                    'description': {
                        'text': 'Shared media'
                    },
                    'media': url,
                    'title': {
                        'text': 'Shared media'
                    }
                } for url in media_urls
            ]
        
        # Post to LinkedIn
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            'https://api.linkedin.com/v2/ugcPosts',
            headers=headers,
            json=post_data
        )
        
        if response.status_code != 201:
            return Response({
                'error': 'Failed to create post on LinkedIn',
                'details': response.text
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse response and save to database
        linkedin_response = response.json()
        post_urn = linkedin_response.get('id', '')
        post_id = post_urn.replace('urn:li:ugcPost:', '')
        
        # Get organization if specified
        organization = None
        if organization_id:
            try:
                organization = LinkedInOrganization.objects.get(
                    account=account,
                    organization_id=organization_id
                )
            except LinkedInOrganization.DoesNotExist:
                pass
        
        # Create post record
        post = LinkedInPost.objects.create(
            account=account,
            organization=organization,
            post_id=post_id,
            urn=post_urn,
            text_content=text_content,
            media_urls=media_urls,
            state='PUBLISHED',
            post_type='UGC_POST',
            published_at=timezone.now()
        )
        
        serializer = LinkedInPostSerializer(post)
        
        return Response({
            'message': 'Post created successfully',
            'post': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'LinkedIn account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error creating LinkedIn post: {e}")
        return Response({
            'error': 'Failed to create post',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Instagram-specific endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_instagram_media(request, account_id):
    """Get Instagram media posts for a specific account"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='instagram'
        )
        
        # Pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # Filter parameters
        media_type = request.GET.get('type')
        
        # Build query
        media_query = InstagramMedia.objects.filter(account=account)
        
        if media_type:
            media_query = media_query.filter(media_type=media_type)
        
        # Get total count
        total_count = media_query.count()
        
        # Apply pagination
        media_posts = media_query[offset:offset + page_size]
        
        serializer = InstagramMediaSerializer(media_posts, many=True)
        
        return Response({
            'media': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Instagram account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching Instagram media: {e}")
        return Response({
            'error': 'Failed to fetch media'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_instagram_media_detail(request, account_id, media_id):
    """Get detailed information about a specific Instagram media post"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='instagram'
        )
        
        media = InstagramMedia.objects.get(
            account=account,
            media_id=media_id
        )
        
        serializer = InstagramMediaSerializer(media)
        
        return Response(serializer.data)
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Instagram account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except InstagramMedia.DoesNotExist:
        return Response({
            'error': 'Media not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching Instagram media detail: {e}")
        return Response({
            'error': 'Failed to fetch media detail'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_instagram_media(request, account_id, media_id):
    """Update Instagram media (caption only - Instagram API doesn't support full editing)"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='instagram'
        )
        
        media = InstagramMedia.objects.get(
            account=account,
            media_id=media_id
        )
        
        # Instagram Basic Display API doesn't support editing posts
        # This endpoint updates our local data only
        new_caption = request.data.get('caption')
        if new_caption is not None:
            media.caption = new_caption
            media.save()
        
        serializer = InstagramMediaSerializer(media)
        
        return Response({
            'message': 'Media updated successfully (local database only)',
            'note': 'Instagram API does not support editing published posts',
            'media': serializer.data
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Instagram account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except InstagramMedia.DoesNotExist:
        return Response({
            'error': 'Media not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating Instagram media: {e}")
        return Response({
            'error': 'Failed to update media'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_instagram_media(request, account_id, media_id):
    """Delete Instagram media from database (Instagram API doesn't support deletion)"""
    try:
        account = UserSocialAccount.objects.get(
            id=account_id,
            user=request.user,
            platform__name='instagram'
        )
        
        media = InstagramMedia.objects.get(
            account=account,
            media_id=media_id
        )
        
        # Instagram Basic Display API doesn't support deleting posts
        # This only removes from our local database
        media.delete()
        
        return Response({
            'message': 'Media removed from database successfully',
            'note': 'Instagram API does not support deleting published posts. This only removes the record from our database.'
        })
        
    except UserSocialAccount.DoesNotExist:
        return Response({
            'error': 'Instagram account not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except InstagramMedia.DoesNotExist:
        return Response({
            'error': 'Media not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting Instagram media: {e}")
        return Response({
            'error': 'Failed to delete media'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)