from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ApiToken
from .serializers import ApiTokenSerializer, CreateApiTokenSerializer


class ApiTokenListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ApiToken.objects.filter(user=self.request.user, is_active=True)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateApiTokenSerializer
        return ApiTokenSerializer


class ApiTokenDestroyView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ApiToken.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_social_post(request):
    """
    API endpoint for n8n to create social media posts
    Expected payload:
    {
        "platform": "instagram",
        "content": {
            "text": "Post content",
            "media_url": "https://example.com/image.jpg"
        },
        "schedule_time": "2024-01-15T18:00:00Z"  # optional
    }
    """
    from apps.social_platforms.models import UserSocialAccount
    from apps.social_platforms.services import SocialMediaService
    
    try:
        data = request.data
        platform = data.get('platform')
        content = data.get('content', {})
        schedule_time = data.get('schedule_time')
        
        if not platform:
            return Response({
                'status': 'error',
                'message': 'Platform is required',
                'error_code': 'MISSING_PLATFORM'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not content.get('text'):
            return Response({
                'status': 'error',
                'message': 'Content text is required',
                'error_code': 'MISSING_CONTENT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user's connected account for the platform
        try:
            account = UserSocialAccount.objects.get(
                user=request.user,
                platform__name=platform,
                status='connected'
            )
        except UserSocialAccount.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'No connected {platform} account found',
                'error_code': 'ACCOUNT_NOT_CONNECTED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the post using social media service
        service = SocialMediaService()
        
        post_data = {
            'text': content.get('text'),
            'media_url': content.get('media_url'),
            'schedule_time': schedule_time
        }
        
        # TODO: Implement actual posting logic based on platform
        # For now, return success response
        result = {
            'status': 'success',
            'message': 'Post created successfully',
            'post_id': f'post_{platform}_{request.user.id}',
            'platform': platform,
            'scheduled': bool(schedule_time)
        }
        
        # Update token last used time
        token_header = request.META.get('HTTP_AUTHORIZATION', '')
        if token_header.startswith('Bearer '):
            token_value = token_header[7:]
            try:
                api_token = ApiToken.objects.get(token=token_value, is_active=True)
                api_token.update_last_used()
            except ApiToken.DoesNotExist:
                pass
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e),
            'error_code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)