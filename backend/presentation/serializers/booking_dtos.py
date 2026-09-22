"""Booking DTOs."""

from rest_framework import serializers


class BookingRequestDTO(serializers.Serializer):
    ticket_quantity = serializers.IntegerField(min_value=1, max_value=5)


class BookingResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    event_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    ticket_quantity = serializers.IntegerField()
