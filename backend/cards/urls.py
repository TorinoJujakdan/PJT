from django.urls import path

from .views import (
    CardCatalogListAPIView,
    CardDiscoveryAPIView,
    MyCardPolicyDetailAPIView,
    MyCardPolicyFromCatalogAPIView,
    MyCardPolicyListCreateAPIView,
)


urlpatterns = [
    path("me/cards/", MyCardPolicyListCreateAPIView.as_view(), name="my-card-policies"),
    path("me/cards/from-catalog/", MyCardPolicyFromCatalogAPIView.as_view(), name="my-card-policy-from-catalog"),
    path("me/cards/<int:card_id>/", MyCardPolicyDetailAPIView.as_view(), name="my-card-policy-detail"),
    path("cards/catalog/", CardCatalogListAPIView.as_view(), name="card-catalog"),
    path("cards/discovery/", CardDiscoveryAPIView.as_view(), name="card-discovery"),
]
