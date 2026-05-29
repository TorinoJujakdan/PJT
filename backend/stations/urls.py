from django.urls import path

from .views import GeocodeAPIView, NearbyStationAPIView, RefreshNearbyStationsAPIView, ReverseGeocodeAPIView


urlpatterns = [
    path("nearby/", NearbyStationAPIView.as_view(), name="stations-nearby"),
    path("geocode/", GeocodeAPIView.as_view(), name="locations-geocode"),
    path("reverse-geocode/", ReverseGeocodeAPIView.as_view(), name="locations-reverse-geocode"),
    path("refresh/", RefreshNearbyStationsAPIView.as_view(), name="stations-refresh"),
]
