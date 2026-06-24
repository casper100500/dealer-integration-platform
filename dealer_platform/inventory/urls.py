from django.urls import path
from rest_framework.routers import DefaultRouter

from dealer_platform.inventory.views import (
    DealerViewSet,
    VehicleDealerOfferView,
    VehicleViewSet,
)

router = DefaultRouter()
router.register("dealers", DealerViewSet, basename="dealer")
router.register("vehicles", VehicleViewSet, basename="vehicle")

urlpatterns = [
    path(
        "vehicles/<int:vehicle_id>/dealers/<int:dealer_id>/offer/",
        VehicleDealerOfferView.as_view(),
        name="vehicle-dealer-offer",
    ),
    *router.urls,
]
