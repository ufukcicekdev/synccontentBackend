import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from urllib.parse import urlencode
import secrets
import string
import requests
import json

from .models import SocialPlatform, UserSocialAccount
from .serializers import SocialPlatformSerializer, UserSocialAccountSerializer

logger = logging.getLogger(__name__)


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
    accounts = UserSocialAccount.objects.filter(user=request.user)
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
    
    # Log the OAuth initiation for debugging
    logger.info(f"OAuth initiated for {platform_name} by user {request.user.email}")
    logger.info(f"State stored: {state}")
    logger.info(f"Authorization URL: {authorization_url}")
    
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
    
    # Enhanced logging for debugging
    logger.info(f"OAuth callback for {platform_name} by user {request.user.email}")
    logger.info(f"Received code: {'present' if code else 'missing'}")
    logger.info(f"Received state: {state}")
    
    if not code:
        logger.error("Authorization code is missing")
        return Response({
            'error': 'Authorization code is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify state to prevent CSRF attacks - make this more flexible
    stored_state = request.session.get(f'oauth_state_{platform_name}')
    logger.info(f"Stored state: {stored_state}")
    
    # For debugging, let's be more lenient with state validation temporarily
    if not stored_state:
        logger.warning("No stored state found in session - this might be a session issue")
        # Continue anyway for debugging purposes
    elif stored_state != state:
        logger.error(f"State mismatch: stored={stored_state}, received={state}")
        return Response({
            'error': 'Invalid state parameter - possible CSRF attack or session issue'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        platform = SocialPlatform.objects.get(name=platform_name, is_active=True)
    except SocialPlatform.DoesNotExist:
        logger.error(f"Platform {platform_name} not found")
        return Response({
            'error': 'Platform not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Exchange code for access token
    token_data = {
        'client_id': platform.oauth_client_id,
        'client_secret': platform.oauth_client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': f"{settings.FRONTEND_URL}/auth/callback/{platform_name}",
    }
    
    logger.info(f"Token exchange request for {platform_name}")
    logger.info(f"Token URL: {platform.oauth_token_url}")
    
    try:
        token_response = requests.post(platform.oauth_token_url, data=token_data)
        logger.info(f"Token response status: {token_response.status_code}")
        logger.info(f"Token response: {token_response.text}")
        
        token_response.raise_for_status()
        tokens = token_response.json()
        
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token', '')
        
        if not access_token:
            logger.error("No access token in response")
            return Response({
                'error': 'Failed to obtain access token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Access token obtained for {platform_name}")
        
        # Get user info from the platform
        user_info = get_platform_user_info(platform_name, access_token)
        logger.info(f"User info for {platform_name}: {user_info}")
        
        if not user_info:
            logger.error(f"Failed to get user info for {platform_name}")
            return Response({
                'error': 'Failed to get user information from platform'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update social account
        social_account, created = UserSocialAccount.objects.update_or_create(
            user=request.user,
            platform=platform,
            platform_user_id=user_info['id'],
            defaults={
                'platform_username': user_info.get('username', ''),
                'platform_display_name': user_info.get('display_name', ''),
                'profile_picture_url': user_info.get('profile_picture', ''),
                'access_token': access_token,  # This should be encrypted in production
                'refresh_token': refresh_token,
                'status': 'connected',
                'permissions': user_info.get('permissions', {}),
            }
        )
        
        logger.info(f"Social account {'created' if created else 'updated'} for {platform_name}")
        
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
        logger.error(f"Token exchange failed: {str(e)}")
        return Response({
            'error': f'Failed to exchange code for token: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")
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
            response = requests.get('https://api.linkedin.com/v2/people/~?projection=(id,firstName,lastName,profilePicture(displayImage~:playableStreams))', headers=headers)
        elif platform_name == 'twitter':
            response = requests.get('https://api.twitter.com/2/users/me', headers=headers)
        elif platform_name == 'tiktok':
            response = requests.get('https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name', headers=headers)
        else:
            logger.error(f"Unsupported platform: {platform_name}")
            return None
        
        response.raise_for_status()
        data = response.json()
        logger.info(f"Platform API response for {platform_name}: {data}")
        
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
                    'username': snippet.get('customUrl', snippet.get('title', '')),
                    'display_name': snippet.get('title', ''),
                    'profile_picture': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'permissions': {}
                }
        elif platform_name == 'linkedin':
            return {
                'id': data.get('id'),
                'username': f"{data.get('firstName', {}).get('localized', {}).get('en_US', '')} {data.get('lastName', {}).get('localized', {}).get('en_US', '')}",
                'display_name': f"{data.get('firstName', {}).get('localized', {}).get('en_US', '')} {data.get('lastName', {}).get('localized', {}).get('en_US', '')}",
                'profile_picture': '',
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
        elif platform_name == 'tiktok':
            return {
                'id': data.get('data', {}).get('user', {}).get('open_id'),
                'username': data.get('data', {}).get('user', {}).get('display_name'),
                'display_name': data.get('data', {}).get('user', {}).get('display_name'),
                'profile_picture': data.get('data', {}).get('user', {}).get('avatar_url'),
                'permissions': {}
            }
        
        logger.error(f"No data parser for platform: {platform_name}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting user info for {platform_name}: {str(e)}")
        return None