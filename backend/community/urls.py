from django.urls import path

from .views import CommunityPostDetailAPIView, CommunityPostListCreateAPIView


urlpatterns = [
    path("posts/", CommunityPostListCreateAPIView.as_view(), name="community-posts"),
    path("posts/<int:post_id>/", CommunityPostDetailAPIView.as_view(), name="community-post-detail"),
]
