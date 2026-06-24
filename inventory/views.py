from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Dealer, InventoryListing, Vehicle
from inventory.serializers import (
    DealerSerializer,
    InventoryListingSerializer,
    InventoryListingWriteSerializer,
    VehicleSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Dealer"]),
    retrieve=extend_schema(tags=["Dealer"]),
)
class DealerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DealerSerializer
    queryset = Dealer.objects.order_by("id")


@extend_schema_view(
    list=extend_schema(tags=["Vehicle"]),
    create=extend_schema(tags=["Vehicle"]),
    retrieve=extend_schema(tags=["Vehicle"]),
    update=extend_schema(tags=["Vehicle"]),
    partial_update=extend_schema(tags=["Vehicle"]),
    destroy=extend_schema(tags=["Vehicle"]),
)
class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.order_by("id")


class VehicleDealerListingView(APIView):
    def get_listing(self, vehicle_id: int, dealer_id: int) -> InventoryListing:
        return get_object_or_404(
            InventoryListing.objects.select_related("dealer", "vehicle"),
            vehicle_id=vehicle_id,
            dealer_id=dealer_id,
        )

    @extend_schema(
        tags=["Vehicle Listing"],
        responses=InventoryListingSerializer,
    )
    def get(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        listing = self.get_listing(vehicle_id, dealer_id)
        serializer = InventoryListingSerializer(listing)
        return Response(serializer.data)

    @extend_schema(
        tags=["Vehicle Listing"],
        request=InventoryListingWriteSerializer,
        responses={
            201: InventoryListingSerializer,
            400: OpenApiResponse(description="Listing already exists."),
        },
    )
    def post(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        dealer = get_object_or_404(Dealer, pk=dealer_id)

        if InventoryListing.objects.filter(
            vehicle=vehicle,
            dealer=dealer,
        ).exists():
            return Response(
                {
                    "detail": (
                        "Inventory listing already exists for this "
                        "vehicle and dealer."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InventoryListingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save(vehicle=vehicle, dealer=dealer)
        response_serializer = InventoryListingSerializer(listing)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Vehicle Listing"],
        request=InventoryListingWriteSerializer,
        responses=InventoryListingSerializer,
    )
    def patch(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        listing = self.get_listing(vehicle_id, dealer_id)
        serializer = InventoryListingWriteSerializer(
            listing,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        response_serializer = InventoryListingSerializer(listing)
        return Response(response_serializer.data)

    @extend_schema(
        tags=["Vehicle Listing"],
        responses={204: OpenApiResponse(description="Listing deleted.")},
    )
    def delete(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        listing = self.get_listing(vehicle_id, dealer_id)
        listing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
