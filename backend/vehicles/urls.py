from django.urls import path

from .views import (
    MyVehicleProfileAPIView,
    MyVehicleProfileDetailAPIView,
    MyVehicleProfilesAPIView,
    SetDefaultVehicleAPIView,
)

urlpatterns = [
    path("me/vehicle/", MyVehicleProfileAPIView.as_view(), name="my-vehicle-profile"),
    path("me/vehicles/", MyVehicleProfilesAPIView.as_view(), name="my-vehicle-profiles"),
    path("me/vehicles/<int:pk>/", MyVehicleProfileDetailAPIView.as_view(), name="my-vehicle-profile-detail"),
    path("me/vehicles/<int:pk>/set-default/", SetDefaultVehicleAPIView.as_view(), name="set-default-vehicle"),
]
