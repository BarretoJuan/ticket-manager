"""Booking controllers: POST /api/v1/events/{event_id}/book (rate limited)."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from domain import exceptions as domain_exceptions

from presentation.di import get_book_ticket_use_case
from presentation.errors import to_http_exception
from presentation.serializers.booking_dtos import BookingRequestDTO, BookingResponseDTO
from presentation.serializers.common_dtos import ErrorResponseDTO
from presentation.utils import build_audit_context


@extend_schema(
    tags=["bookings"],
    parameters=[
        OpenApiParameter("event_id", str, OpenApiParameter.PATH, description="Event UUID")
    ],
    request=BookingRequestDTO,
    responses={
        201: BookingResponseDTO,
        400: ErrorResponseDTO,
        401: ErrorResponseDTO,
        404: ErrorResponseDTO,
        409: ErrorResponseDTO,
        429: ErrorResponseDTO,
    },
)
class BookingCreateView(APIView):
    """POST /api/v1/events/{event_id}/book — book tickets (rate limited)."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "book"

    def post(self, request, event_id):
        dto = BookingRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        try:
            booking = get_book_ticket_use_case().execute(
                event_id=event_id,
                user_id=request.user.id,
                quantity=dto.validated_data["ticket_quantity"],
                audit=build_audit_context(request),
            )
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)
        return Response(BookingResponseDTO(booking).data, status=status.HTTP_201_CREATED)