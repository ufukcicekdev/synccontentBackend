import requests
import logging
from django.utils import timezone
from .models import (
    UserSocialAccount, LinkedInOrganization, LinkedInPost,
    YouTubeAnalytics, LinkedInAnalytics, InstagramAnalytics, TwitterAnalytics, TikTokAnalytics, InstagramMedia
)

logger = logging.getLogger(__name__)


class YouTubeAnalyticsService:
    """Service to fetch and update YouTube channel analytics"""
    
    BASE_URL = 'https://www.googleapis.com/youtube/v3'
    
    @classmethod
    def fetch_channel_analytics(cls, account: UserSocialAccount):
        """
        Fetch YouTube channel analytics for a connected account
        
        Args:
            account: UserSocialAccount instance for YouTube
            
        Returns:
            dict: Analytics data or None if failed
        """
        if account.platform.name != 'youtube':
            logger.error(f"Account {account.id} is not a YouTube account")
            return None
        
        try:
            # Decrypt access token
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                # If decryption fails, try using the token directly (for development)
                access_token = account.access_token
                
            if not access_token:
                logger.error(f"No valid access token for account {account.id}")
                return None
                
            logger.info(f"Attempting to fetch YouTube analytics for account {account.id}")
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Fetch channel information including statistics
            url = f'{cls.BASE_URL}/channels'
            params = {
                'part': 'statistics,snippet',
                'mine': 'true'
            }
            
            logger.info(f"Making YouTube API request to: {url}")
            logger.info(f"Request params: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            logger.info(f"YouTube API response status: {response.status_code}")
            logger.info(f"YouTube API response: {response.text[:500]}")
            
            # If unauthorized, try to refresh the token
            if response.status_code == 401:
                logger.info(f"Token expired for account {account.id}, attempting refresh...")
                
                refresh_token = account.decrypt_token(account.refresh_token)
                if refresh_token:
                    new_access_token = cls.refresh_access_token(account, refresh_token)
                    if new_access_token:
                        # Retry with new token
                        headers['Authorization'] = f'Bearer {new_access_token}'
                        response = requests.get(url, headers=headers, params=params)
                        logger.info(f"Retry after refresh - Status: {response.status_code}")
                    else:
                        logger.error(f"Failed to refresh token for account {account.id}")
                        return None
                else:
                    logger.error(f"No refresh token available for account {account.id}")
                    return None
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get('items'):
                logger.warning(f"No channel data found for account {account.id}")
                return None
            
            channel_data = data['items'][0]
            statistics = channel_data.get('statistics', {})
            snippet = channel_data.get('snippet', {})
            
            analytics_data = {
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'total_view_count': int(statistics.get('viewCount', 0)),
                'last_updated': timezone.now()
            }
            
            # Update or create analytics record
            analytics, created = YouTubeAnalytics.objects.get_or_create(
                account=account,
                defaults=analytics_data
            )
            
            if not created:
                # Update existing analytics
                for key, value in analytics_data.items():
                    setattr(analytics, key, value)
                analytics.save()
            
            logger.info(f"Updated YouTube analytics for account {account.id}")
            return analytics_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching YouTube analytics for account {account.id}: {e}")
            
            # If it's a 401 error and we couldn't refresh, mark account as expired
            if hasattr(e, 'response') and e.response and e.response.status_code == 401:
                account.status = 'expired'
                account.save()
                logger.info(f"Marked account {account.id} as expired due to 401 error")
            
            return None
        except Exception as e:
            logger.error(f"Error fetching YouTube analytics for account {account.id}: {e}")
            return None
    
    @classmethod
    def fetch_recent_videos(cls, account: UserSocialAccount, max_results=5):
        """
        Fetch recent videos from the YouTube channel
        
        Args:
            account: UserSocialAccount instance for YouTube
            max_results: Number of recent videos to fetch
            
        Returns:
            list: Recent videos data or empty list if failed
        """
        if account.platform.name != 'youtube':
            return []
        
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                return []
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # First, get the channel ID
            channel_response = requests.get(
                f'{cls.BASE_URL}/channels',
                headers=headers,
                params={
                    'part': 'id',
                    'mine': 'true'
                }
            )
            
            channel_response.raise_for_status()
            channel_data = channel_response.json()
            
            if not channel_data.get('items'):
                return []
            
            channel_id = channel_data['items'][0]['id']
            
            # Get recent videos
            search_response = requests.get(
                f'{cls.BASE_URL}/search',
                headers=headers,
                params={
                    'part': 'snippet',
                    'channelId': channel_id,
                    'maxResults': max_results,
                    'order': 'date',
                    'type': 'video'
                }
            )
            
            search_response.raise_for_status()
            search_data = search_response.json()
            
            videos = []
            for item in search_data.get('items', []):
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'][:200],
                    'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                    'published_at': item['snippet']['publishedAt'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                })
            
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching recent videos for account {account.id}: {e}")
            return []
    
    @classmethod
    def get_video_details(cls, account: UserSocialAccount, video_id: str):
        """Get detailed information about a specific video"""
        if account.platform.name != 'youtube':
            return None
            
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                return None
                
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f'{cls.BASE_URL}/videos',
                headers=headers,
                params={
                    'part': 'snippet,status,localizations',
                    'id': video_id
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get('items'):
                return None
                
            video = data['items'][0]
            snippet = video.get('snippet', {})
            status = video.get('status', {})
            localizations = video.get('localizations', {})
            
            return {
                'video_id': video['id'],
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'category_id': snippet.get('categoryId', ''),
                'tags': snippet.get('tags', []),
                'privacy_status': status.get('privacyStatus', ''),
                'default_language': snippet.get('defaultLanguage', ''),
                'default_audio_language': snippet.get('defaultAudioLanguage', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'published_at': snippet.get('publishedAt', ''),
                'url': f"https://www.youtube.com/watch?v={video['id']}",
                'live_broadcast_content': snippet.get('liveBroadcastContent', ''),
                'made_for_kids': status.get('madeForKids', False),
                'self_declared_made_for_kids': status.get('selfDeclaredMadeForKids', False)
            }
            
        except Exception as e:
            logger.error(f"Error fetching video details for {video_id}: {e}")
            return None
    
    @classmethod
    def update_video(cls, account: UserSocialAccount, video_id: str, video_data: dict):
        """Update video metadata (title, description, category, tags, privacy, language)"""
        if account.platform.name != 'youtube':
            return None
            
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                return None
                
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare update payload with snippet
            update_data = {
                'id': video_id,
                'snippet': {}
            }
            
            # Add snippet fields that are being updated
            if 'title' in video_data:
                update_data['snippet']['title'] = video_data['title']
            if 'description' in video_data:
                update_data['snippet']['description'] = video_data['description']
            if 'category_id' in video_data:
                update_data['snippet']['categoryId'] = video_data['category_id']
            if 'tags' in video_data:
                update_data['snippet']['tags'] = video_data['tags']
            if 'default_language' in video_data:
                update_data['snippet']['defaultLanguage'] = video_data['default_language']
            if 'default_audio_language' in video_data:
                update_data['snippet']['defaultAudioLanguage'] = video_data['default_audio_language']
                
            # Add status fields if being updated
            if 'privacy_status' in video_data or 'made_for_kids' in video_data:
                update_data['status'] = {}
                if 'privacy_status' in video_data:
                    update_data['status']['privacyStatus'] = video_data['privacy_status']
                if 'made_for_kids' in video_data:
                    update_data['status']['madeForKids'] = video_data['made_for_kids']
                    update_data['status']['selfDeclaredMadeForKids'] = video_data['made_for_kids']
            
            # Determine which parts to update
            parts = ['snippet']
            if 'status' in update_data:
                parts.append('status')
                
            response = requests.put(
                f'{cls.BASE_URL}/videos',
                headers=headers,
                params={'part': ','.join(parts)},
                json=update_data
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Successfully updated video {video_id} for account {account.id}")
            return result
            
        except Exception as e:
            logger.error(f"Error updating video {video_id}: {e}")
            return None
    
    @classmethod
    def get_supported_languages(cls, account: UserSocialAccount):
        """Get supported languages from YouTube API for general platform use"""
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                logger.warning(f"No access token available for account {account.id}")
                return cls._get_fallback_languages()
                
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Get supported languages with region preference
            region_code = cls.get_user_region(account)
            
            # Fetch supported languages from YouTube API
            response = requests.get(
                f'{cls.BASE_URL}/i18nLanguages',
                headers=headers,
                params={
                    'part': 'snippet',
                    'hl': region_code.lower()  # Use region for localized language names
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            languages = []
            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                language_code = item.get('id', '')
                language_name = snippet.get('name', '')
                
                if language_code and language_name:
                    languages.append({
                        'code': language_code,
                        'name': language_name
                    })
                
            # Sort languages alphabetically by name
            languages.sort(key=lambda x: x['name'])
            logger.info(f"Successfully fetched {len(languages)} languages from YouTube API")
            return languages
            
        except Exception as e:
            logger.error(f"Error fetching supported languages from YouTube API: {e}")
            return cls._get_fallback_languages()
    
    @classmethod
    def _get_fallback_languages(cls):
        """Return fallback list of common languages"""
        return [
            {'code': 'en', 'name': 'English'},
            {'code': 'es', 'name': 'Spanish'},
            {'code': 'fr', 'name': 'French'},
            {'code': 'de', 'name': 'German'},
            {'code': 'it', 'name': 'Italian'},
            {'code': 'pt', 'name': 'Portuguese'},
            {'code': 'ru', 'name': 'Russian'},
            {'code': 'ja', 'name': 'Japanese'},
            {'code': 'ko', 'name': 'Korean'},
            {'code': 'zh', 'name': 'Chinese'},
            {'code': 'hi', 'name': 'Hindi'},
            {'code': 'ar', 'name': 'Arabic'},
            {'code': 'tr', 'name': 'Turkish'},
            {'code': 'nl', 'name': 'Dutch'},
            {'code': 'sv', 'name': 'Swedish'},
            {'code': 'da', 'name': 'Danish'},
            {'code': 'no', 'name': 'Norwegian'},
            {'code': 'fi', 'name': 'Finnish'},
            {'code': 'pl', 'name': 'Polish'}
        ]
    
    @classmethod
    def get_user_region(cls, account: UserSocialAccount):
        """Get user's region from YouTube channel info"""
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                return 'US'  # Default fallback
                
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Get channel info to determine region
            response = requests.get(
                f'{cls.BASE_URL}/channels',
                headers=headers,
                params={
                    'part': 'snippet,localizations',
                    'mine': 'true'
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('items'):
                channel = data['items'][0]
                snippet = channel.get('snippet', {})
                # Get country from channel, fallback to US
                return snippet.get('country', 'US')
                
            return 'US'
            
        except Exception as e:
            logger.error(f"Error fetching user region: {e}")
            return 'US'  # Default fallback
    
    @classmethod
    def get_video_categories(cls, account: UserSocialAccount):
        """Get available video categories for YouTube platform (not video-specific)"""
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                logger.warning(f"No access token available for account {account.id}")
                return cls._get_fallback_categories()
                
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Get user's region for more accurate categories
            region_code = cls.get_user_region(account)
            
            # Fetch video categories from YouTube API
            response = requests.get(
                f'{cls.BASE_URL}/videoCategories',
                headers=headers,
                params={
                    'part': 'snippet',
                    'regionCode': region_code
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            categories = []
            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                # Only include assignable categories
                if snippet.get('assignable', False):
                    category_id = item.get('id', '')
                    category_title = snippet.get('title', '')
                    
                    if category_id and category_title:
                        categories.append({
                            'id': category_id,
                            'title': category_title
                        })
                    
            # Sort categories alphabetically
            categories.sort(key=lambda x: x['title'])
            logger.info(f"Successfully fetched {len(categories)} categories from YouTube API for region {region_code}")
            return categories
            
        except Exception as e:
            logger.error(f"Error fetching video categories from YouTube API: {e}")
            return cls._get_fallback_categories()
    
    @classmethod
    def _get_fallback_categories(cls):
        """Return fallback list of common YouTube categories"""
        return [
            {'id': '1', 'title': 'Film & Animation'},
            {'id': '2', 'title': 'Autos & Vehicles'},
            {'id': '10', 'title': 'Music'},
            {'id': '15', 'title': 'Pets & Animals'},
            {'id': '17', 'title': 'Sports'},
            {'id': '19', 'title': 'Travel & Events'},
            {'id': '20', 'title': 'Gaming'},
            {'id': '22', 'title': 'People & Blogs'},
            {'id': '23', 'title': 'Comedy'},
            {'id': '24', 'title': 'Entertainment'},
            {'id': '25', 'title': 'News & Politics'},
            {'id': '26', 'title': 'Howto & Style'},
            {'id': '27', 'title': 'Education'},
            {'id': '28', 'title': 'Science & Technology'},
            {'id': '29', 'title': 'Nonprofits & Activism'}
        ]
    
    @classmethod
    def refresh_access_token(cls, account: UserSocialAccount, refresh_token: str):
        """Refresh YouTube access token using refresh token"""
        try:
            from .models import SocialPlatform
            platform = SocialPlatform.objects.get(name='youtube')
            
            token_data = {
                'client_id': platform.oauth_client_id,
                'client_secret': platform.oauth_client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_data
            )
            
            if response.status_code == 200:
                tokens = response.json()
                new_access_token = tokens.get('access_token')
                
                if new_access_token:
                    # Update the stored token
                    account.access_token = new_access_token
                    
                    # Update expiry if provided
                    if tokens.get('expires_in'):
                        from django.utils import timezone
                        import datetime
                        account.token_expires_at = timezone.now() + datetime.timedelta(
                            seconds=int(tokens['expires_in'])
                        )
                    
                    account.save()
                    logger.info(f"Successfully refreshed token for account {account.id}")
                    return new_access_token
                    
            logger.error(f"Failed to refresh token for account {account.id}: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error refreshing token for account {account.id}: {e}")
            return None


class InstagramAnalyticsService:
    """Enhanced service to fetch Instagram analytics and media"""
    
    @classmethod
    def fetch_account_analytics(cls, account: UserSocialAccount):
        """Fetch comprehensive Instagram account analytics and media"""
        if account.platform.name != 'instagram':
            return None
        
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                logger.error(f"No access token available for Instagram account {account.id}")
                return None
            
            # Initialize analytics data with defaults
            analytics_data = {
                'last_updated': timezone.now(),
                'follower_count': 0,
                'following_count': 0,
                'media_count': 0,
                'account_type': '',
                'total_likes': 0,
                'total_comments': 0,
                'average_likes_per_post': 0,
                'average_comments_per_post': 0,
                'engagement_rate': 0
            }
            
            # Fetch basic account info
            account_info = cls._fetch_account_info(access_token)
            if account_info:
                analytics_data.update({
                    'media_count': account_info.get('media_count', 0),
                    'follower_count': account_info.get('followers_count', 0),
                    'following_count': account_info.get('follows_count', 0),
                    'account_type': 'BUSINESS'  # Instagram Graph API is for business accounts
                })
                logger.info(f"Updated basic info for Instagram account {account.id}")
            
            # Fetch user media and calculate engagement metrics
            try:
                media_data = cls._fetch_user_media(access_token, account)
                if media_data:
                    media_list = media_data.get('media', [])
                    if media_list:
                        total_likes = sum(media.get('like_count', 0) for media in media_list)
                        total_comments = sum(media.get('comments_count', 0) for media in media_list)
                        
                        analytics_data.update({
                            'total_likes': total_likes,
                            'total_comments': total_comments,
                            'average_likes_per_post': total_likes / len(media_list) if media_list else 0,
                            'average_comments_per_post': total_comments / len(media_list) if media_list else 0,
                        })
                        
                        # Calculate engagement rate (basic calculation)
                        total_engagement = total_likes + total_comments
                        if analytics_data['follower_count'] > 0:
                            analytics_data['engagement_rate'] = (total_engagement / (analytics_data['follower_count'] * len(media_list))) * 100
                        
                        logger.info(f"Calculated engagement metrics for {len(media_list)} media posts")
            except Exception as e:
                logger.warning(f"Could not fetch media for Instagram account {account.id}: {e}")
            
            # Update or create analytics record
            analytics, created = InstagramAnalytics.objects.get_or_create(
                account=account,
                defaults=analytics_data
            )
            
            if not created:
                for key, value in analytics_data.items():
                    setattr(analytics, key, value)
                analytics.save()
            
            logger.info(f"Successfully updated Instagram analytics for account {account.id}")
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error fetching Instagram analytics for account {account.id}: {e}")
            return None
    
    @classmethod
    def _fetch_account_info(cls, access_token):
        """Fetch basic account information using Instagram Graph API"""
        try:
            # First get Facebook pages
            response = requests.get(
                'https://graph.facebook.com/v18.0/me/accounts',
                params={
                    'access_token': access_token,
                    'fields': 'instagram_business_account,name'
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch Facebook pages: {response.status_code} - {response.text}")
                return None
            
            pages_data = response.json()
            
            # Find Instagram business account
            for page in pages_data.get('data', []):
                if 'instagram_business_account' in page:
                    ig_account_id = page['instagram_business_account']['id']
                    
                    # Get Instagram account details
                    ig_response = requests.get(
                        f'https://graph.facebook.com/v18.0/{ig_account_id}',
                        params={
                            'access_token': access_token,
                            'fields': 'id,username,name,profile_picture_url,media_count,followers_count,follows_count'
                        }
                    )
                    
                    if ig_response.status_code == 200:
                        return ig_response.json()
            
            return None
                
        except Exception as e:
            logger.error(f"Error fetching Instagram account info: {e}")
            return None
    
    @classmethod
    def _fetch_user_media(cls, access_token, account):
        """Fetch user's Instagram media posts using Instagram Graph API"""
        try:
            # First get Instagram business account ID
            pages_response = requests.get(
                'https://graph.facebook.com/v18.0/me/accounts',
                params={
                    'access_token': access_token,
                    'fields': 'instagram_business_account'
                }
            )
            
            if pages_response.status_code != 200:
                logger.error(f"Failed to fetch pages: {pages_response.status_code}")
                return None
            
            pages_data = pages_response.json()
            ig_account_id = None
            
            for page in pages_data.get('data', []):
                if 'instagram_business_account' in page:
                    ig_account_id = page['instagram_business_account']['id']
                    break
            
            if not ig_account_id:
                logger.error("No Instagram business account found")
                return None
            
            # Get media from Instagram account
            response = requests.get(
                f'https://graph.facebook.com/v18.0/{ig_account_id}/media',
                params={
                    'access_token': access_token,
                    'fields': 'id,media_type,media_url,permalink,caption,timestamp,like_count,comments_count',
                    'limit': 25
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch Instagram media: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            media_list = []
            
            # Process each media item
            for media_item in data.get('data', []):
                try:
                    media_data = {
                        'media_id': media_item.get('id'),
                        'media_type': media_item.get('media_type', 'IMAGE'),
                        'media_url': media_item.get('media_url', ''),
                        'permalink': media_item.get('permalink', ''),
                        'caption': media_item.get('caption', ''),
                        'timestamp': media_item.get('timestamp'),
                        'like_count': media_item.get('like_count', 0),
                        'comments_count': media_item.get('comments_count', 0),
                    }
                    
                    # Create or update media record in database
                    cls._create_or_update_media(media_data, account)
                    media_list.append(media_data)
                    
                except Exception as media_error:
                    logger.error(f"Error processing media item: {media_error}")
                    continue
            
            logger.info(f"Successfully processed {len(media_list)} media items")
            return {'media': media_list, 'total_count': len(media_list)}
            
        except Exception as e:
            logger.error(f"Error fetching Instagram media: {e}")
            return None
    
    @classmethod
    def _create_or_update_media(cls, media_data, account):
        """Create or update Instagram media record"""
        try:
            # Parse timestamp
            timestamp = None
            if media_data.get('timestamp'):
                from datetime import datetime
                timestamp = datetime.fromisoformat(media_data['timestamp'].replace('Z', '+00:00'))
            
            media, created = InstagramMedia.objects.get_or_create(
                account=account,
                media_id=media_data['media_id'],
                defaults={
                    'media_type': media_data.get('media_type', 'IMAGE'),
                    'media_url': media_data.get('media_url', ''),
                    'permalink': media_data.get('permalink', ''),
                    'caption': media_data.get('caption', ''),
                    'like_count': media_data.get('like_count', 0),
                    'comments_count': media_data.get('comments_count', 0),
                    'timestamp': timestamp
                }
            )
            
            if not created:
                # Update existing media
                media.media_type = media_data.get('media_type', media.media_type)
                media.media_url = media_data.get('media_url', media.media_url)
                media.permalink = media_data.get('permalink', media.permalink)
                media.caption = media_data.get('caption', media.caption)
                media.like_count = media_data.get('like_count', media.like_count)
                media.comments_count = media_data.get('comments_count', media.comments_count)
                if timestamp:
                    media.timestamp = timestamp
                media.save()
            
            return media
            
        except Exception as e:
            logger.error(f"Error creating/updating Instagram media: {e}")
            return None
    
    @classmethod
    def fetch_recent_media(cls, account, limit=20):
        """Fetch recent media posts for an account"""
        try:
            media_queryset = InstagramMedia.objects.filter(
                account=account
            ).order_by('-timestamp', '-created_at')[:limit]
            
            from .serializers import InstagramMediaSerializer
            serializer = InstagramMediaSerializer(media_queryset, many=True)
            return serializer.data
            
        except Exception as e:
            logger.error(f"Error fetching recent Instagram media: {e}")
            return []
    
    @classmethod
    def get_media_details(cls, account, media_id):
        """Get detailed information about a specific media post"""
        try:
            media = InstagramMedia.objects.get(
                account=account,
                media_id=media_id
            )
            
            from .serializers import InstagramMediaSerializer
            serializer = InstagramMediaSerializer(media)
            return serializer.data
            
        except InstagramMedia.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching Instagram media details: {e}")
            return None
    
    @classmethod
    def update_media_caption(cls, account, media_id, new_caption):
        """Update media caption (local database only - Instagram API doesn't support editing)"""
        try:
            media = InstagramMedia.objects.get(
                account=account,
                media_id=media_id
            )
            
            # Note: Instagram Basic Display API doesn't support editing captions
            # This only updates our local database record
            media.caption = new_caption
            media.save()
            
            from .serializers import InstagramMediaSerializer
            serializer = InstagramMediaSerializer(media)
            return serializer.data
            
        except InstagramMedia.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error updating Instagram media caption: {e}")
            return None
    
    @classmethod
    def delete_media(cls, account, media_id):
        """Delete media from database (Instagram API doesn't support deletion via Basic Display API)"""
        try:
            media = InstagramMedia.objects.get(
                account=account,
                media_id=media_id
            )
            
            # Note: Instagram Basic Display API doesn't support deleting posts
            # This only removes from our local database
            media.delete()
            return True
            
        except InstagramMedia.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error deleting Instagram media: {e}")
            return False


class LinkedInAnalyticsService:
    """Enhanced service to fetch LinkedIn account analytics, posts, and organizations"""
    
    @classmethod
    def fetch_account_analytics(cls, account: UserSocialAccount):
        """Fetch comprehensive LinkedIn account analytics"""
        if account.platform.name != 'linkedin':
            return None
        
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                logger.error(f"No access token available for LinkedIn account {account.id}")
                return None
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            # Initialize analytics data with defaults
            analytics_data = {
                'last_updated': timezone.now(),
                'connection_count': 0,
                'follower_count': 0,
                'post_count': 0,
                'profile_views': 0,
                'search_appearances': 0,
                'total_organizations': 0,
                'managed_pages': 0,
                'recent_posts_count': 0,
                'recent_total_likes': 0,
                'recent_total_comments': 0,
                'recent_total_shares': 0,
                'recent_total_views': 0,
                'average_post_engagement': 0
            }
            
            # Fetch and update basic profile information
            profile_data = cls._fetch_profile_info(headers)
            if profile_data:
                # Update account information
                if 'sub' in profile_data:  # LinkedIn user ID
                    account.platform_user_id = profile_data['sub']
                if 'email' in profile_data:
                    account.platform_username = profile_data['email']
                if 'name' in profile_data:
                    account.platform_display_name = profile_data['name']
                if 'picture' in profile_data:
                    account.profile_picture_url = profile_data['picture']
                account.save()
                logger.info(f"Updated account info for LinkedIn account {account.id}")
            else:
                logger.warning(f"Could not fetch profile info for LinkedIn account {account.id}")
            
            # Try to fetch organizations (requires r_organization_social scope)
            try:
                organizations = cls._fetch_organizations(headers, account)
                analytics_data['total_organizations'] = len(organizations)
                analytics_data['managed_pages'] = len([org for org in organizations if org.get('can_post', False)])
                logger.info(f"Found {len(organizations)} organizations for account {account.id}")
            except Exception as e:
                logger.warning(f"Could not fetch organizations for LinkedIn account {account.id}: {e}")
            
            # Try to fetch user posts (requires w_member_social scope for posting, r_member_social for reading)
            try:
                posts_data = cls._fetch_user_posts(headers, account)
                analytics_data['post_count'] = posts_data.get('total_count', 0)
                
                # Calculate engagement metrics from recent posts
                recent_posts = posts_data.get('posts', [])
                if recent_posts:
                    analytics_data['recent_posts_count'] = len(recent_posts)
                    total_likes = sum(post.get('like_count', 0) for post in recent_posts)
                    total_comments = sum(post.get('comment_count', 0) for post in recent_posts)
                    total_shares = sum(post.get('share_count', 0) for post in recent_posts)
                    total_views = sum(post.get('view_count', 0) for post in recent_posts)
                    
                    analytics_data.update({
                        'recent_total_likes': total_likes,
                        'recent_total_comments': total_comments,
                        'recent_total_shares': total_shares,
                        'recent_total_views': total_views,
                        'average_post_engagement': (total_likes + total_comments + total_shares) / len(recent_posts) if recent_posts else 0
                    })
                    logger.info(f"Calculated engagement metrics for {len(recent_posts)} posts")
            except Exception as e:
                logger.warning(f"Could not fetch posts for LinkedIn account {account.id}: {e}")
            
            # Note: Connection count API (r_1st_connections_size) is heavily restricted
            # Most applications cannot access this, so we'll skip it for now
            logger.info(f"Skipping connection count - requires special LinkedIn approval")
            
            # Update or create analytics record
            analytics, created = LinkedInAnalytics.objects.get_or_create(
                account=account,
                defaults=analytics_data
            )
            
            if not created:
                for key, value in analytics_data.items():
                    setattr(analytics, key, value)
                analytics.save()
            
            logger.info(f"Successfully updated LinkedIn analytics for account {account.id}")
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn analytics for account {account.id}: {e}")
            return None
    
    @classmethod
    def _fetch_profile_info(cls, headers):
        """Fetch basic profile information"""
        try:
            response = requests.get(
                'https://api.linkedin.com/v2/userinfo',
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch LinkedIn profile: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile: {e}")
            return None
    
    @classmethod
    def _fetch_organizations(cls, headers, account):
        """Fetch user's organizations and company pages"""
        try:
            # Use the correct LinkedIn v2 API endpoint for organization access control lists
            response = requests.get(
                'https://api.linkedin.com/v2/organizationAcls',
                headers=headers,
                params={
                    'q': 'roleAssignee',
                    'projection': '(elements*(organization~(id,localizedName,localizedDescription,localizedWebsite,logoV2,locations*,industries*),roleAssignee,state))'
                }
            )
            
            logger.info(f"Organization ACL response status: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"Organization ACL request failed: {response.status_code} - {response.text[:500]}")
                return []
            
            organizations = []
            data = response.json()
            
            for element in data.get('elements', []):
                try:
                    org_info = element.get('organization~', {})
                    if not org_info or 'id' not in org_info:
                        continue
                    
                    # Extract organization data
                    org_data = {
                        'account': account,
                        'organization_id': str(org_info['id']),
                        'name': org_info.get('localizedName', 'Unknown Organization'),
                        'description': org_info.get('localizedDescription', ''),
                        'website_url': org_info.get('localizedWebsite', ''),
                        'user_role': element.get('role', 'MEMBER'),
                        'is_admin': 'ADMIN' in str(element.get('role', '')),
                        'can_post': element.get('state') == 'APPROVED'
                    }
                    
                    # Extract industry information
                    if 'industries' in org_info and org_info['industries']:
                        org_data['industry'] = org_info['industries'][0].get('localizedName', '')
                    
                    # Extract logo URL
                    if 'logoV2' in org_info:
                        org_data['logo_url'] = cls._extract_media_url(org_info['logoV2'])
                    
                    # Create or update organization record
                    org, created = LinkedInOrganization.objects.get_or_create(
                        account=account,
                        organization_id=org_data['organization_id'],
                        defaults=org_data
                    )
                    
                    if not created:
                        # Update existing organization
                        for key, value in org_data.items():
                            if key not in ['account', 'organization_id']:
                                setattr(org, key, value)
                        org.save()
                    
                    organizations.append(org_data)
                    logger.info(f"Processed organization: {org_data['name']} (ID: {org_data['organization_id']})")
                    
                except Exception as org_error:
                    logger.error(f"Error processing organization element: {org_error}")
                    continue
            
            logger.info(f"Successfully processed {len(organizations)} organizations")
            return organizations
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn organizations: {e}")
            return []
    
    @classmethod
    def _fetch_user_posts(cls, headers, account):
        """Fetch user's LinkedIn posts/activities"""
        try:
            if not account.platform_user_id:
                logger.warning(f"No platform_user_id for account {account.id}")
                return {'posts': [], 'total_count': 0}
            
            # Use the correct LinkedIn v2 UGC Posts API
            response = requests.get(
                'https://api.linkedin.com/v2/ugcPosts',
                headers=headers,
                params={
                    'q': 'authors',
                    'authors': f'urn:li:person:{account.platform_user_id}',
                    'count': 20,  # Reduced count for reliability
                    'sortBy': 'LAST_MODIFIED'
                }
            )
            
            logger.info(f"UGC Posts response status: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"UGC Posts request failed: {response.status_code} - {response.text[:500]}")
                return {'posts': [], 'total_count': 0}
            
            posts_data = {'posts': [], 'total_count': 0}
            data = response.json()
            
            # Get total count from paging info
            paging = data.get('paging', {})
            posts_data['total_count'] = paging.get('total', 0)
            
            # Process each post
            for element in data.get('elements', []):
                try:
                    post_data = cls._parse_ugc_post(element, account)
                    if post_data:
                        posts_data['posts'].append(post_data)
                        
                        # Create or update post record in database
                        cls._create_or_update_post(post_data, account)
                        
                except Exception as post_error:
                    logger.error(f"Error processing post element: {post_error}")
                    continue
            
            logger.info(f"Successfully processed {len(posts_data['posts'])} posts")
            return posts_data
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn posts: {e}")
            return {'posts': [], 'total_count': 0}
    
    @classmethod
    def _parse_ugc_post(cls, element, account):
        """Parse UGC post data from LinkedIn API"""
        try:
            post_id = element.get('id', '').replace('urn:li:ugcPost:', '')
            specific_content = element.get('specificContent', {})
            ugc_header = element.get('ugcPostHeader', {})
            social_detail = element.get('socialDetail', {})
            
            # Extract text content
            text_content = ''
            if 'ugcPostHeader' in element:
                text_content = ugc_header.get('text', '')
            
            # Extract media URLs
            media_urls = []
            if 'com.linkedin.ugc.ShareContent' in specific_content:
                share_content = specific_content['com.linkedin.ugc.ShareContent']
                for media in share_content.get('media', []):
                    media_url = cls._extract_media_url(media)
                    if media_url:
                        media_urls.append(media_url)
            
            # Extract engagement metrics
            engagement = social_detail.get('totalSocialActivityCounts', {})
            
            post_data = {
                'post_id': post_id,
                'urn': element.get('id', ''),
                'text_content': text_content,
                'media_urls': media_urls,
                'like_count': engagement.get('numLikes', 0),
                'comment_count': engagement.get('numComments', 0),
                'share_count': engagement.get('numShares', 0),
                'view_count': engagement.get('numViews', 0),
                'published_at': timezone.datetime.fromtimestamp(element.get('created', {}).get('time', 0) / 1000, tz=timezone.utc) if element.get('created') else None,
                'last_modified_at': timezone.datetime.fromtimestamp(element.get('lastModified', {}).get('time', 0) / 1000, tz=timezone.utc) if element.get('lastModified') else None,
                'state': element.get('lifecycleState', 'PUBLISHED'),
                'post_type': 'UGC_POST'
            }
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error parsing UGC post: {e}")
            return None
    
    @classmethod
    def _create_or_update_post(cls, post_data, account):
        """Create or update LinkedIn post record"""
        try:
            post, created = LinkedInPost.objects.get_or_create(
                account=account,
                post_id=post_data['post_id'],
                defaults=post_data
            )
            
            if not created:
                for key, value in post_data.items():
                    if key not in ['account', 'post_id']:
                        setattr(post, key, value)
                post.save()
            
            return post
            
        except Exception as e:
            logger.error(f"Error creating/updating LinkedIn post: {e}")
            return None
    
    @classmethod
    def _fetch_connections(cls, headers):
        """Fetch connection count (limited by LinkedIn API permissions)"""
        try:
            # This endpoint requires r_1st_connections_size scope which is restricted
            response = requests.get(
                'https://api.linkedin.com/v2/people-search',
                headers=headers,
                params={'facets': 'List(network:(F))'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {'total': data.get('paging', {}).get('total', 0)}
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn connections: {e}")
            return None
    
    @classmethod
    def _fetch_company_follower_count(cls, headers, org_id):
        """Fetch follower count for company page"""
        try:
            response = requests.get(
                f'https://api.linkedin.com/v2/networkSizes/{org_id}',
                headers=headers,
                params={'edgeType': 'CompanyFollowedByMember'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('firstDegreeSize', 0)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching company follower count: {e}")
            return None
    
    @classmethod
    def _extract_media_url(cls, media_object):
        """Extract media URL from LinkedIn media object"""
        try:
            if isinstance(media_object, dict):
                # Handle different media object structures
                if 'digitalmediaAsset' in media_object:
                    return media_object['digitalmediaAsset']
                elif 'com.linkedin.digitalmedia.mediaartifact.StillImage' in media_object:
                    return media_object['com.linkedin.digitalmedia.mediaartifact.StillImage']['storageArtifact']['com.linkedin.digitalmedia.mediaartifact.StorageArtifact']['fileIdentifyingUrlPathSegment']
                elif 'url' in media_object:
                    return media_object['url']
            
            return ''
            
        except Exception as e:
            logger.error(f"Error extracting media URL: {e}")
            return ''


class SocialAnalyticsService:
    """Main service to coordinate analytics fetching for all platforms"""
    
    PLATFORM_SERVICES = {
        'youtube': YouTubeAnalyticsService,
        'instagram': InstagramAnalyticsService,
        'linkedin': LinkedInAnalyticsService,  # Add LinkedIn service
    }
    
    @classmethod
    def update_account_analytics(cls, account: UserSocialAccount):
        """Update analytics for a specific account"""
        service_class = cls.PLATFORM_SERVICES.get(account.platform.name)
        
        if service_class:
            if hasattr(service_class, 'fetch_channel_analytics'):
                return service_class.fetch_channel_analytics(account)
            elif hasattr(service_class, 'fetch_account_analytics'):
                return service_class.fetch_account_analytics(account)
        
        logger.warning(f"No analytics service available for platform: {account.platform.name}")
        return None
    
    @classmethod
    def update_all_user_analytics(cls, user):
        """Update analytics for all connected accounts of a user"""
        accounts = UserSocialAccount.objects.filter(
            user=user,
            status='connected'
        )
        
        results = {}
        for account in accounts:
            result = cls.update_account_analytics(account)
            results[account.platform.name] = result
        
        return results
