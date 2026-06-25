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

from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle
from dealer_platform.inventory.serializers import (
    DealerOfferSerializer,
    DealerOfferWriteSerializer,
    DealerSerializer,
    VehicleSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Dealer"]),
    retrieve=extend_schema(tags=["Dealer"]),
)
class DealerViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose read-only dealer endpoints."""

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
    """Expose vehicle CRUD endpoints."""

    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.order_by("id")


class VehicleDealerOfferView(APIView):
    """Manage a dealer offer for a specific vehicle and dealer."""

    def get_offer(self, vehicle_id: int, dealer_id: int) -> DealerOffer:
        """Return the dealer offer or raise a 404 response."""
        return get_object_or_404(
            DealerOffer.objects.select_related("dealer", "vehicle"),
            vehicle_id=vehicle_id,
            dealer_id=dealer_id,
        )

    @extend_schema(
        tags=["Dealer Offer"],
        responses=DealerOfferSerializer,
    )
    def get(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        """Return the dealer offer for the vehicle and dealer."""
        offer = self.get_offer(vehicle_id, dealer_id)
        serializer = DealerOfferSerializer(offer)
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealer Offer"],
        request=DealerOfferWriteSerializer,
        responses={
            201: DealerOfferSerializer,
            400: OpenApiResponse(description="Dealer offer already exists."),
        },
    )
    def post(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        """Create the dealer offer for the vehicle and dealer."""
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        dealer = get_object_or_404(Dealer, pk=dealer_id)

        if DealerOffer.objects.filter(
            vehicle=vehicle,
            dealer=dealer,
        ).exists():
            return Response(
                {
                    "detail": (
                        "Dealer offer already exists for this "
                        "vehicle and dealer."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DealerOfferWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(vehicle=vehicle, dealer=dealer)
        response_serializer = DealerOfferSerializer(offer)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Dealer Offer"],
        request=DealerOfferWriteSerializer,
        responses=DealerOfferSerializer,
    )
    def patch(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        """Partially update the dealer offer for the vehicle and dealer."""
        offer = self.get_offer(vehicle_id, dealer_id)
        serializer = DealerOfferWriteSerializer(
            offer,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        offer = serializer.save()
        response_serializer = DealerOfferSerializer(offer)
        return Response(response_serializer.data)

    @extend_schema(
        tags=["Dealer Offer"],
        responses={204: OpenApiResponse(description="Dealer offer deleted.")},
    )
    def delete(
        self,
        request: Request,
        vehicle_id: int,
        dealer_id: int,
    ) -> Response:
        """Delete the dealer offer for the vehicle and dealer."""
        offer = self.get_offer(vehicle_id, dealer_id)
        offer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
