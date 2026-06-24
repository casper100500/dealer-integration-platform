from rest_framework import serializers

from inventory.models import Dealer, DealerOffer, Vehicle


class DealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealer
        fields = [
            "id",
            "name",
            "external_id",
            "website_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class VehicleSerializer(serializers.ModelSerializer):
    dealer = DealerSerializer(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "vin",
            "plate_number",
            "year",
            "make",
            "model",
            "exterior_color",
            "body_style",
            "fuel_type",
            "engine",
            "transmission",
            "created_at",
            "updated_at",
            "dealer",
        ]
        read_only_fields = ["id", "dealer", "created_at", "updated_at"]


class DealerOfferSerializer(serializers.ModelSerializer):
    dealer = DealerSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)

    class Meta:
        model = DealerOffer
        fields = [
            "id",
            "dealer",
            "vehicle",
            "price",
            "currency",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "dealer",
            "vehicle",
            "created_at",
            "updated_at",
        ]


class DealerOfferWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerOffer
        fields = ["price", "currency"]
