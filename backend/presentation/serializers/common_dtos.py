"""Shared DTOs used across endpoints (error responses, health)."""

from rest_framework import serializers


class ErrorResponseDTO(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField(required=False, allow_null=True)


class HealthResponseDTO(serializers.Serializer):
    status = serializers.CharField()
    server = serializers.CharField()
    database = serializers.CharField()
    timestamp = serializers.DateTimeField()
