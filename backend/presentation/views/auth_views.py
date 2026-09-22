"""Authentication controllers: /login and /register."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from domain import exceptions as domain_exceptions

from presentation.di import get_login_user_use_case, get_register_user_use_case
from presentation.errors import to_http_exception
from presentation.serializers.auth_dtos import (
    LoginRequestDTO,
    RegisterRequestDTO,
    TokenResponseDTO,
    UserResponseDTO,
)
from presentation.serializers.common_dtos import ErrorResponseDTO


@extend_schema(
    tags=["auth"],
    request=LoginRequestDTO,
    responses={
        200: TokenResponseDTO,
        401: ErrorResponseDTO,
        429: ErrorResponseDTO,
    },
)
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        dto = LoginRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        try:
            user = get_login_user_use_case().execute(
                email=dto.validated_data["email"],
                password=dto.validated_data["password"],
            )
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)

        refresh = RefreshToken()
        refresh["user_id"] = str(user.id)
        refresh["role"] = user.role
        body = TokenResponseDTO(
            {"access": str(refresh.access_token), "refresh": str(refresh)}
        ).data
        return Response(body, status=status.HTTP_200_OK)


@extend_schema(
    tags=["auth"],
    request=RegisterRequestDTO,
    responses={
        201: UserResponseDTO,
        400: ErrorResponseDTO,
        409: ErrorResponseDTO,
        429: ErrorResponseDTO,
    },
)
class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        dto = RegisterRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        try:
            user = get_register_user_use_case().execute(
                email=dto.validated_data["email"],
                password=dto.validated_data["password"],
            )
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)

        body = UserResponseDTO(user).data
        return Response(body, status=status.HTTP_201_CREATED)
