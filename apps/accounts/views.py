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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'detail': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


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