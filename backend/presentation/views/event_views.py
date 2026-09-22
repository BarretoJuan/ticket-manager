"""Event controllers.

* ``EventCollectionView`` -> GET  /api/v1/events (list, authenticated)
* ``EventCollectionView`` -> POST /api/v1/events (create, admins only)
* ``EventDetailView`` -> PATCH  /api/v1/events/{event_id} (edit, admins only)
* ``EventDetailView`` -> DELETE /api/v1/events/{event_id} (soft delete, admins only)

GET /api/v1/events supports pagination (20 events per page) and filters:
``code``, ``name``, ``date_from``/``date_to``, ``availability``, ``page``.
"""

from datetime import datetime, time, timezone
from math import ceil

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)

from domain import exceptions as domain_exceptions
from domain.repositories.event_repository import EventQuery

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
    EventListQueryDTO,
    EventListResponseDTO,
    EventResponseDTO,
    EventUpdateRequestDTO,
)
from presentation.utils import build_audit_context

PAGE_SIZE = 20


def _start_of_day_utc(value) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _end_of_day_utc(value) -> datetime:
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def _build_page_response(request, page, page_result, page_size):
    """DRF-style envelope: count, next, previous, results."""
    count = page_result.total
    last_page = max(1, ceil(count / page_size))

    def page_url(target: int) -> str:
        query = request.GET.copy()
        query["page"] = str(target)
        return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")

    return {
        "count": count,
        "next": page_url(page + 1) if page < last_page else None,
        "previous": page_url(page - 1) if page > 1 else None,
        "results": [EventResponseDTO(event).data for event in page_result.items],
    }


@extend_schema_view(
    get=extend_schema(
        tags=["events"],
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("code", OpenApiTypes.STR, required=False),
            OpenApiParameter("name", OpenApiTypes.STR, required=False),
            OpenApiParameter("date_from", OpenApiTypes.DATE, required=False),
            OpenApiParameter("date_to", OpenApiTypes.DATE, required=False),
            OpenApiParameter(
                "availability",
                OpenApiTypes.STR,
                enum=["available", "sold_out"],
                required=False,
            ),
        ],
        responses={
            200: EventListResponseDTO,
            400: ErrorResponseDTO,
            401: ErrorResponseDTO,
        },
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
        dto = EventListQueryDTO(data=request.query_params)
        dto.is_valid(raise_exception=True)
        params = dto.validated_data

        page = params.get("page", 1)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        query = EventQuery(
            code=params.get("code") or None,
            name=params.get("name") or None,
            date_from=_start_of_day_utc(date_from) if date_from else None,
            date_to=_end_of_day_utc(date_to) if date_to else None,
            availability=params.get("availability"),
            offset=(page - 1) * PAGE_SIZE,
            limit=PAGE_SIZE,
        )
        page_result = get_list_events_use_case().execute(query=query)
        return Response(_build_page_response(request, page, page_result, PAGE_SIZE))

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
