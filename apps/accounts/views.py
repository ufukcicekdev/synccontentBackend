from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.conf import settings

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
GOOGLE_AUTH_AVAILABLE = True

    


from .models import User, UserProfile, SystemLog
from .serializers import UserSerializer, UserRegistrationSerializer, CustomTokenObtainPairSerializer, SystemLogSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that accepts email and returns user data along with tokens"""
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        # Validate password
        password = serializer.validated_data['password']
        try:
            validate_password(password)
        except ValidationError as e:
            return Response({
                'detail': 'Password validation failed',
                'errors': list(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = serializer.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Serialize user data
        user_serializer = UserSerializer(user)
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': user_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny
def logout(request):
    """Logout user by blacklisting refresh token"""
    
    # Handle GET requests with helpful message
    if request.method == 'GET':
        return Response({
            'error': 'Logout requires POST method with refresh token',
            'usage': 'POST /api/auth/logout/ with {"refresh": "your_refresh_token"}'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required for logout'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to blacklist the refresh token
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        return Response({
            'detail': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Even if token blacklisting fails, we consider logout successful
        # This handles cases where token is already expired or invalid
        return Response({
            'detail': 'Logged out (token was invalid or expired)',
            'warning': str(e)
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get user profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({
            'error': 'Both old and new passwords are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if old password is correct
    if not request.user.check_password(old_password):
        return Response({
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate new password
    try:
        validate_password(new_password, request.user)
    except ValidationError as e:
        return Response({
            'error': 'Password validation failed',
            'details': list(e.messages)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    request.user.set_password(new_password)
    request.user.save()
    
    return Response({
        'message': 'Password changed successfully'
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """Delete user account"""
    user = request.user
    user.delete()
    
    return Response({
        'message': 'Account deleted successfully'
    }, status=status.HTTP_200_OK)


class SystemLogListView(ListAPIView):
    """List system logs with filtering and pagination"""
    serializer_class = SystemLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = SystemLog.objects.all().order_by('-created')
        
        # Filter by level
        level = self.request.query_params.get('level', None)
        if level:
            queryset = queryset.filter(level=level)
        
        # Filter by logger name
        logger_name = self.request.query_params.get('logger', None)
        if logger_name:
            queryset = queryset.filter(logger_name__icontains=logger_name)
        
        # Filter by user (staff only)
        if self.request.user.is_staff:
            user_id = self.request.query_params.get('user', None)
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            # Non-staff users can only see their own logs
            queryset = queryset.filter(user=self.request.user)
        
        return queryset


@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """Google Sign-In for authentication"""
    if not GOOGLE_AUTH_AVAILABLE:
        return Response({
            'error': 'Google authentication libraries are not installed'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    print("request.data.get('token')",request.data.get('token'))

    token = request.data.get('token')
    
    if not token:
        return Response({
            'error': 'Google token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Verify the Google ID token
        google_client_id = settings.SOCIAL_MEDIA_CREDENTIALS.get('GOOGLE_AUTH', {}).get('CLIENT_ID')
        print("google_client_id",google_client_id)
        if not google_client_id:
            return Response({
                'error': 'Google authentication is not configured'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            google_client_id
        )
        
        # Check if token is from correct issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        # Extract user information
        google_user_id = idinfo['sub']
        email = idinfo['email']
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')
        full_name = idinfo.get('name', f'{first_name} {last_name}'.strip())
        picture_url = idinfo.get('picture', '')
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
            # Update user info if needed
            if not user.full_name and full_name:
                user.full_name = full_name
                user.save()
        except User.DoesNotExist:
            # Create new user
            # Generate a unique username based on email
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                full_name=full_name,
                is_verified=True  # Google verified users
            )
            
            # Create user profile
            UserProfile.objects.create(user=user)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add custom claims
        access_token['email'] = user.email
        access_token['full_name'] = user.full_name
        access_token['user_id'] = user.id
        
        # Serialize user data
        user_serializer = UserSerializer(user)
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'error': f'Invalid Google token: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Google authentication failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_register(request):
    """Google Sign-In for registration (same as login since Google handles verification)"""
    # Google registration is the same as login since Google verifies the user
    return google_login(request)