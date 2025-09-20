import requests
import logging
from django.utils import timezone
from .models import UserSocialAccount, SocialAccountAnalytics

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
                'view_count': int(statistics.get('viewCount', 0)),
                'last_updated': timezone.now()
            }
            
            # Update or create analytics record
            analytics, created = SocialAccountAnalytics.objects.get_or_create(
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
    """Service to fetch Instagram analytics"""
    
    @classmethod
    def fetch_account_analytics(cls, account: UserSocialAccount):
        """Fetch Instagram account analytics"""
        if account.platform.name != 'instagram':
            return None
        
        try:
            access_token = account.decrypt_token(account.access_token)
            if not access_token:
                return None
            
            # Instagram Basic Display API
            response = requests.get(
                'https://graph.instagram.com/me',
                params={
                    'fields': 'account_type,media_count',
                    'access_token': access_token
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            analytics_data = {
                'media_count': data.get('media_count', 0),
                'last_updated': timezone.now()
            }
            
            analytics, created = SocialAccountAnalytics.objects.get_or_create(
                account=account,
                defaults=analytics_data
            )
            
            if not created:
                for key, value in analytics_data.items():
                    setattr(analytics, key, value)
                analytics.save()
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error fetching Instagram analytics for account {account.id}: {e}")
            return None


class SocialAnalyticsService:
    """Main service to coordinate analytics fetching for all platforms"""
    
    PLATFORM_SERVICES = {
        'youtube': YouTubeAnalyticsService,
        'instagram': InstagramAnalyticsService,
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