"""Authentication glue: custom backend + JWT authentication that honours soft
deletion."""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings

from infrastructure.orm.models import UserORM


class UserBackend:
    """Django auth backend: authenticate by email + password, ignore soft-deleted
    users."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or not password:
            return None
        try:
            user = UserORM.objects.get(
                email__iexact=email.strip(), deleted_at__isnull=True
            )
        except UserORM.DoesNotExist:
            return None
        if user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        try:
            return UserORM.objects.get(pk=user_id, deleted_at__isnull=True)
        except UserORM.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        return user.is_active and user.deleted_at is None


class TicketJWTAuthentication(JWTAuthentication):
    """JWT auth that rejects soft-deleted and inactive users."""

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification")

        user = UserORM.objects.filter(pk=user_id, deleted_at__isnull=True).first()
        if user is None or not user.is_active:
            raise AuthenticationFailed("User not found or no longer active")
        return user
