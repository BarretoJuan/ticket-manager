"""Event controllers.

* ``EventCollectionView`` -> GET  /api/v1/events (list, authenticated)
* ``EventCollectionView`` -> POST /api/v1/events (create, admins only)
* ``EventDetailView`` -> PATCH  /api/v1/events/{event_id} (edit, admins only)
* ``EventDetailView`` -> DELETE /api/v1/events/{event_id} (soft delete, admins only)
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from domain import exceptions as domain_exceptions

from presentation.di import (
    get_create_event_use_case,
    get_delete_event_use_case,
    get_list_events_use_case,
    get_update_event_use_case,
)
from presentation.errors import to_http_exception
from presentation.permissions import IsAdmin
from presentation.serializers.common_dtos import ErrorResponseDTO
from presentation.serializers.event_dtos import (
    EventCreateRequestDTO,
    EventResponseDTO,
    EventUpdateRequestDTO,
)
from presentation.utils import build_audit_context


@extend_schema_view(
    get=extend_schema(
        tags=["events"],
        responses={200: EventResponseDTO(many=True), 401: ErrorResponseDTO},
    ),
    post=extend_schema(
        tags=["events"],
        request=EventCreateRequestDTO,
        responses={
            201: EventResponseDTO,
            400: ErrorResponseDTO,
            401: ErrorResponseDTO,
            403: ErrorResponseDTO,
            409: ErrorResponseDTO,
        },
    ),
)
class EventCollectionView(APIView):
    """List and create events."""

    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return super().get_permissions()

    def get(self, request):
        code = request.query_params.get("code") or None
        events = get_list_events_use_case().execute(code=code)
        return Response([EventResponseDTO(e).data for e in events])

    def post(self, request):
        dto = EventCreateRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        try:
            event = get_create_event_use_case().execute(
                **dto.validated_data, audit=build_audit_context(request)
            )
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)
        return Response(EventResponseDTO(event).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(
        tags=["events"],
        request=EventUpdateRequestDTO,
        responses={
            200: EventResponseDTO,
            400: ErrorResponseDTO,
            401: ErrorResponseDTO,
            403: ErrorResponseDTO,
            404: ErrorResponseDTO,
            409: ErrorResponseDTO,
        },
    ),
    delete=extend_schema(
        tags=["events"],
        responses={
            204: None,
            401: ErrorResponseDTO,
            403: ErrorResponseDTO,
            404: ErrorResponseDTO,
        },
    ),
)
class EventDetailView(APIView):
    """Edit and soft-delete a single event (admins only)."""

    permission_classes = [IsAdmin]

    def patch(self, request, event_id):
        dto = EventUpdateRequestDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        try:
            event = get_update_event_use_case().execute(
                event_id=event_id,
                audit=build_audit_context(request),
                **dto.validated_data,
            )
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)
        return Response(EventResponseDTO(event).data)

    def delete(self, request, event_id):
        try:
            get_delete_event_use_case().execute(
                event_id=event_id, audit=build_audit_context(request)
            )
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
