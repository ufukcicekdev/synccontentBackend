from django.core.management.base import BaseCommand
from apps.social_platforms.models import SocialPlatform


class Command(BaseCommand):
    help = 'Populate social media platforms with default configurations'

    def handle(self, *args, **options):
        platforms_data = [
            {
                'name': 'instagram',
                'display_name': 'Instagram',
                'icon_class': 'fab fa-instagram',
                'color_class': 'bg-gradient-to-r from-purple-500 to-pink-500',
                'oauth_authorization_url': 'https://api.instagram.com/oauth/authorize',
                'oauth_token_url': 'https://api.instagram.com/oauth/access_token',
                'oauth_scope': 'user_profile,user_media',
                # These need to be set with real values from Instagram Developer Portal
                'oauth_client_id': '',  # Set this with your Instagram App ID
                'oauth_client_secret': '',  # Set this with your Instagram App Secret
            },
            {
                'name': 'youtube',
                'display_name': 'YouTube',
                'icon_class': 'fab fa-youtube',
                'color_class': 'bg-red-600',
                'oauth_authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'oauth_token_url': 'https://oauth2.googleapis.com/token',
                'oauth_scope': 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload',
                'oauth_client_id': '',  # Set with Google OAuth credentials
                'oauth_client_secret': '',
            },
            {
                'name': 'linkedin',
                'display_name': 'LinkedIn',
                'icon_class': 'fab fa-linkedin',
                'color_class': 'bg-blue-700',
                'oauth_authorization_url': 'https://www.linkedin.com/oauth/v2/authorization',
                'oauth_token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
                'oauth_scope': 'openid profile email w_member_social r_organization_social',
                'oauth_client_id': '',  # Set with LinkedIn OAuth credentials
                'oauth_client_secret': '',
            },
            {
                'name': 'twitter',
                'display_name': 'Twitter/X',
                'icon_class': 'fab fa-twitter',
                'color_class': 'bg-black',
                'oauth_authorization_url': 'https://twitter.com/i/oauth2/authorize',
                'oauth_token_url': 'https://api.twitter.com/2/oauth2/token',
                'oauth_scope': 'tweet.read tweet.write users.read offline.access',
                'oauth_client_id': '',  # Set with Twitter OAuth credentials
                'oauth_client_secret': '',
            },
            {
                'name': 'tiktok',
                'display_name': 'TikTok',
                'icon_class': 'fab fa-tiktok',
                'color_class': 'bg-black',
                'oauth_authorization_url': 'https://www.tiktok.com/v2/auth/authorize/',
                'oauth_token_url': 'https://open.tiktokapis.com/v2/oauth/token/',
                'oauth_scope': 'user.info.basic video.list video.upload',
                'oauth_client_id': '',  # Set with TikTok OAuth credentials
                'oauth_client_secret': '',
            }
        ]

        created_count = 0
        updated_count = 0

        for platform_data in platforms_data:
            platform, created = SocialPlatform.objects.update_or_create(
                name=platform_data['name'],
                defaults=platform_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created platform: {platform.display_name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated platform: {platform.display_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPopulated {created_count} new platforms and updated {updated_count} existing platforms.'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                '\nIMPORTANT: You need to set OAuth client credentials for each platform:'
            )
        )
        self.stdout.write('1. Instagram: Get credentials from https://developers.facebook.com/apps/')
        self.stdout.write('2. YouTube: Get credentials from https://console.cloud.google.com/')
        self.stdout.write('3. LinkedIn: Get credentials from https://www.linkedin.com/developers/apps')
        self.stdout.write('4. Twitter: Get credentials from https://developer.twitter.com/apps')
        self.stdout.write('5. TikTok: Get credentials from https://developers.tiktok.com/')