from django.urls import path

from .views import LoginAPIView, LogoutAPIView, MeAPIView, SignupAPIView, UsernameAvailabilityAPIView

urlpatterns = [
    path("accounts/signup/", SignupAPIView.as_view(), name="accounts-signup"),
    path("accounts/username-availability/", UsernameAvailabilityAPIView.as_view(), name="accounts-username-availability"),
    path("accounts/login/", LoginAPIView.as_view(), name="accounts-login"),
    path("accounts/logout/", LogoutAPIView.as_view(), name="accounts-logout"),
    path("accounts/me/", MeAPIView.as_view(), name="accounts-me"),
]
