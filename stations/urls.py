from django.urls import path
from .views import RecommendationAPIView

app_name = 'stations'

urlpatterns = [
    path('api/recommendations/', RecommendationAPIView.as_view(), name='recommendations'),
]
