"""Event DTOs: create / update payloads and response representation."""

from decimal import Decimal

from rest_framework import serializers


class EventCreateRequestDTO(serializers.Serializer):
    name = serializers.CharField(min_length=5, max_length=100)
    code = serializers.RegexField(regex=r"^EVT-\d{4}-[A-Z]{2}$")
    date = serializers.DateTimeField()
    total_capacity = serializers.IntegerField(min_value=1)
    ticket_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )


class EventUpdateRequestDTO(serializers.Serializer):
    name = serializers.CharField(min_length=5, max_length=100, required=False)
    code = serializers.RegexField(regex=r"^EVT-\d{4}-[A-Z]{2}$", required=False)
    date = serializers.DateTimeField(required=False)
    total_capacity = serializers.IntegerField(min_value=1, required=False)
    ticket_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"), required=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("at least one field must be provided")
        return attrs


class EventResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    deleted_at = serializers.DateTimeField(allow_null=True)
    name = serializers.CharField()
    code = serializers.CharField()
    date = serializers.DateTimeField()
    total_capacity = serializers.IntegerField()
    available_tickets = serializers.IntegerField()
    ticket_price = serializers.DecimalField(max_digits=12, decimal_places=2)
