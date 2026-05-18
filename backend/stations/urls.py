from django.urls import path

from .views import NearbyStationAPIView


urlpatterns = [
    path("nearby/", NearbyStationAPIView.as_view(), name="stations-nearby"),
]
