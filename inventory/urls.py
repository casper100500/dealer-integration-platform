from django.urls import path
from rest_framework.routers import DefaultRouter

from inventory.views import (
    DealerViewSet,
    VehicleDealerListingView,
    VehicleViewSet,
)

router = DefaultRouter()
router.register("Dealer", DealerViewSet, basename="dealer")
router.register("Vehicle", VehicleViewSet, basename="vehicle")

urlpatterns = [
    path(
        "Vehicle/<int:vehicle_id>/Dealer/<int:dealer_id>/listing/",
        VehicleDealerListingView.as_view(),
        name="vehicle-dealer-listing",
    ),
    *router.urls,
]
