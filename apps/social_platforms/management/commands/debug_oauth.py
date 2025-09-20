from django.core.management.base import BaseCommand
from apps.social_platforms.models import SocialPlatform
from django.conf import settings


class Command(BaseCommand):
    help = 'Debug OAuth configuration for social media platforms'

    def add_arguments(self, parser):
        parser.add_argument(
            '--platform',
            type=str,
            help='Specific platform to debug (instagram, youtube, linkedin, twitter, tiktok)',
        )

    def handle(self, *args, **options):
        platform_name = options.get('platform')
        
        if platform_name:
            try:
                platform = SocialPlatform.objects.get(name=platform_name)
                platforms = [platform]
            except SocialPlatform.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Platform "{platform_name}" not found')
                )
                return
        else:
            platforms = SocialPlatform.objects.all()

        self.stdout.write(
            self.style.SUCCESS('\n=== OAuth Configuration Debug ===\n')
        )

        for platform in platforms:
            self.stdout.write(f'\n{platform.display_name} ({platform.name}):')
            self.stdout.write(f'  Active: {platform.is_active}')
            self.stdout.write(f'  Authorization URL: {platform.oauth_authorization_url}')
            self.stdout.write(f'  Token URL: {platform.oauth_token_url}')
            self.stdout.write(f'  Scope: {platform.oauth_scope}')
            self.stdout.write(f'  Client ID configured: {"✓" if platform.oauth_client_id else "✗"}')
            self.stdout.write(f'  Client Secret configured: {"✓" if platform.oauth_client_secret else "✗"}')
            
            # Show what the redirect URI would be
            redirect_uri = f"{settings.FRONTEND_URL}/auth/callback/{platform.name}"
            self.stdout.write(f'  Redirect URI: {redirect_uri}')
            
            # Check if ready for OAuth
            is_ready = bool(platform.oauth_client_id and platform.oauth_client_secret and platform.is_active)
            status_icon = "✓" if is_ready else "✗"
            self.stdout.write(f'  Ready for OAuth: {status_icon}')
            
            if not is_ready:
                self.stdout.write(
                    self.style.WARNING(f'    Missing configuration for {platform.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('\n=== Setup Instructions ===\n')
        )
        self.stdout.write('For each platform, you need to:')
        self.stdout.write('1. Create OAuth app in platform\'s developer portal')
        self.stdout.write('2. Configure redirect URI (shown above)')
        self.stdout.write('3. Set client ID and secret in Django admin or database')
        self.stdout.write('\nPlatform developer portals:')
        self.stdout.write('- Instagram: https://developers.facebook.com/apps/')
        self.stdout.write('- YouTube: https://console.cloud.google.com/')
        self.stdout.write('- LinkedIn: https://www.linkedin.com/developers/apps')
        self.stdout.write('- Twitter: https://developer.twitter.com/apps')
        self.stdout.write('- TikTok: https://developers.tiktok.com/')