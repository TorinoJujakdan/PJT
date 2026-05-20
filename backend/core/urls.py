from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from stations.views import RecommendationQuoteAPIView


def health_check(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("cards.urls")),
    path("api/v1/", include("vehicles.urls")),
    path("api/v1/stations/", include("stations.urls")),
    path("api/v1/recommendations/quote/", RecommendationQuoteAPIView.as_view(), name="recommendations-quote"),
]
