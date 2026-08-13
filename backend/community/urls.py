from django.urls import path

from .views import CommunityPostDetailAPIView, CommunityPostListCreateAPIView, CommunityPostStarAPIView

urlpatterns = [
    path("posts/", CommunityPostListCreateAPIView.as_view(), name="community-posts"),
    path("posts/<int:post_id>/star/", CommunityPostStarAPIView.as_view(), name="community-post-star"),
    path("posts/<int:post_id>/", CommunityPostDetailAPIView.as_view(), name="community-post-detail"),
]
