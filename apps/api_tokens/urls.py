from django.urls import path
from .views import ApiTokenListCreateView, ApiTokenDestroyView, create_social_post

urlpatterns = [
    path('tokens/', ApiTokenListCreateView.as_view(), name='api-tokens'),
    path('tokens/<int:pk>/', ApiTokenDestroyView.as_view(), name='api-token-destroy'),
    path('social/post/', create_social_post, name='social-post'),
]