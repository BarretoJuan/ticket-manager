"""Health controller: GET /api/v1/health — server + DB status."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from domain.utils import utcnow

from infrastructure.db import check_database_connection

from presentation.serializers.common_dtos import HealthResponseDTO


@extend_schema(
    tags=["health"],
    responses={
        200: HealthResponseDTO,
        503: HealthResponseDTO,
    },
)
class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        database_status = check_database_connection()
        healthy = database_status == "connected"
        body = HealthResponseDTO(
            {
                "status": "ok" if healthy else "degraded",
                "server": "ok",
                "database": database_status,
                "timestamp": utcnow(),
            }
        ).data
        return Response(body, status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE)