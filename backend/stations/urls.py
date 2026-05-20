from django.urls import path

from .views import NearbyStationAPIView, GeocodeAPIView


urlpatterns = [
    path("nearby/", NearbyStationAPIView.as_view(), name="stations-nearby"),
    path("geocode/", GeocodeAPIView.as_view(), name="locations-geocode"),
]
