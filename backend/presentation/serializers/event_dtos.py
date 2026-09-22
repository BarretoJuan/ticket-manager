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


class EventListQueryDTO(serializers.Serializer):
    """Query params for GET /api/v1/events (filters + page)."""

    code = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    availability = serializers.ChoiceField(
        choices=["available", "sold_out"], required=False
    )
    page = serializers.IntegerField(min_value=1, required=False, default=1)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError("date_from must be <= date_to")
        return attrs


class EventListResponseDTO(serializers.Serializer):
    """Paginated envelope returned by GET /api/v1/events."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True, required=False)
    previous = serializers.URLField(allow_null=True, required=False)
    results = EventResponseDTO(many=True)
