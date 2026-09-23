"""SAT controllers.

* ``SatSyncView``        -> POST /api/v1/sat/sync[?force=true]  (start, async)
* ``SatSyncStatusView``  -> GET  /api/v1/sat/sync/{history_id}  (status poll)
* ``SatHistoryListView`` -> GET  /api/v1/sat/history            (paginated list)

All endpoints are admin-only: the sync writes into the SAT tables and the
history records which user triggered the download.
"""

import math

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from domain import exceptions as domain_exceptions
from domain.repositories.sat_repository import SatHistoryQuery

from presentation.di import (
    get_sat_list_history_use_case,
    get_sat_sync_runner,
    get_sat_sync_use_case,
)
from presentation.errors import to_http_exception
from presentation.permissions import IsAdmin
from presentation.serializers.common_dtos import ErrorResponseDTO
from presentation.serializers.sat_dtos import (
    SatHistoryListResponseDTO,
    SatHistoryQueryDTO,
    SatHistoryResponseDTO,
    SatSyncSkipDTO,
    SatSyncStartedDTO,
)
from presentation.utils import build_audit_context

PAGE_SIZE = 20


def _parse_force_flag(query_params) -> bool:
    return query_params.get("force", "").strip().lower() in ("1", "true", "yes", "on")


def _build_history_page_response(request, page, page_result):
    """DRF-style envelope: count, next, previous, results."""
    count = page_result.total
    last_page = max(1, math.ceil(count / PAGE_SIZE))

    def page_url(target: int) -> str:
        query = request.GET.copy()
        query["page"] = str(target)
        return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")

    return {
        "count": count,
        "next": page_url(page + 1) if page < last_page else None,
        "previous": page_url(page - 1) if page > 1 else None,
        "results": [SatHistoryResponseDTO(item).data for item in page_result.items],
    }


@extend_schema_view(
    post=extend_schema(
        tags=["sat"],
        request=None,  # no request body — only the optional ?force=true query param
        parameters=[
            OpenApiParameter(
                "force",
                OpenApiTypes.BOOL,
                required=False,
                description="Bypass the cooldown window (time-based)",
            )
        ],
        responses={
            200: SatSyncSkipDTO,
            202: SatSyncStartedDTO,
            401: ErrorResponseDTO,
            403: ErrorResponseDTO,
            409: ErrorResponseDTO,
        },
    ),
)
class SatSyncView(APIView):
    """POST /api/v1/sat/sync — start the sync; never blocks on the download."""

    permission_classes = [IsAdmin]

    def post(self, request):
        force = _parse_force_flag(request.query_params)
        result = get_sat_sync_runner().start(
            force=force,
            user_id=request.user.id,
            audit=build_audit_context(request),
        )

        if result.status == "started":
            return Response(
                SatSyncStartedDTO(
                    {
                        "history_id": result.history.id,
                        "status": "processing",
                        "started_at": result.history.started_at,
                        "force": force,
                    }
                ).data,
                status=status.HTTP_202_ACCEPTED,
            )

        if result.status == "cooldown_skip":
            return Response(
                SatSyncSkipDTO(
                    {
                        "status": "skipped",
                        "reason": "cooldown",
                        "next_allowed_at": result.next_allowed_at,
                        "last_sync": (
                            SatHistoryResponseDTO(result.last_sync).data
                            if result.last_sync
                            else None
                        ),
                    }
                ).data
            )

        # in_progress
        return Response(
            {
                "detail": (result.reason or "a SAT sync is already in progress"),
                "history_id": str(result.history.id) if result.history else None,
            },
            status=status.HTTP_409_CONFLICT,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["sat"],
        responses={
            200: SatHistoryResponseDTO,
            401: ErrorResponseDTO,
            403: ErrorResponseDTO,
            404: ErrorResponseDTO,
        },
    ),
)
class SatSyncStatusView(APIView):
    """GET /api/v1/sat/sync/{history_id} — poll the status of a sync run."""

    permission_classes = [IsAdmin]

    def get(self, request, history_id):
        try:
            history = get_sat_sync_use_case().get_history(history_id)
        except domain_exceptions.DomainError as exc:
            raise to_http_exception(exc)
        return Response(SatHistoryResponseDTO(history).data)


@extend_schema_view(
    get=extend_schema(
        tags=["sat"],
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
        ],
        responses={
            200: SatHistoryListResponseDTO,
            400: ErrorResponseDTO,
            401: ErrorResponseDTO,
            403: ErrorResponseDTO,
        },
    ),
)
class SatHistoryListView(APIView):
    """GET /api/v1/sat/history — last processed files, 20 per page, newest first."""

    permission_classes = [IsAdmin]

    def get(self, request):
        dto = SatHistoryQueryDTO(data=request.query_params)
        dto.is_valid(raise_exception=True)
        page = dto.validated_data["page"]
        query = SatHistoryQuery(offset=(page - 1) * PAGE_SIZE, limit=PAGE_SIZE)
        page_result = get_sat_list_history_use_case().execute(query=query)
        return Response(_build_history_page_response(request, page, page_result))
