"""Database access helpers (health checks)."""

from django.db import connection


def check_database_connection() -> str:
    """Return ``"connected"`` or an error description (never raises)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "connected"
    except Exception as exc:  # noqa: BLE001 - health endpoint reports any failure
        return f"error: {exc}"
