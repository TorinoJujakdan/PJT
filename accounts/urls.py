from django.urls import path
from .views import (
    RegisterAPIView, LoginAPIView, ProfileAPIView,
    CardListAPIView, UserCardAPIView
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('profile/', ProfileAPIView.as_view(), name='profile'),
    path('cards/', CardListAPIView.as_view(), name='card_list'),
    path('cards/<int:card_id>/', UserCardAPIView.as_view(), name='user_card'),
]
