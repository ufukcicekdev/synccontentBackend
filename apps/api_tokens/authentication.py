from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .models import ApiToken

User = get_user_model()


class ApiTokenAuthentication(BaseAuthentication):
    """
    Custom authentication class for API tokens
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return None
            
        try:
            keyword, token = auth_header.split()
        except ValueError:
            return None
            
        if keyword.lower() != self.keyword.lower():
            return None
            
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        try:
            api_token = ApiToken.objects.select_related('user').get(
                token=token, 
                is_active=True
            )
        except ApiToken.DoesNotExist:
            return None  # Let other authentication methods try
            
        if not api_token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted')
            
        return (api_token.user, api_token)

    def authenticate_header(self, request):
        return self.keyword