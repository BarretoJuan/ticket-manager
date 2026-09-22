"""Auth DTOs: login / register / tokens."""

from rest_framework import serializers


class LoginRequestDTO(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RegisterRequestDTO(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, min_length=8, trim_whitespace=False
    )


class TokenResponseDTO(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class UserResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    role = serializers.CharField()
    created_at = serializers.DateTimeField()