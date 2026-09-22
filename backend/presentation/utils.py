"""Request metadata helpers for controllers."""

from domain.entities.log_entry import AuditContext


def build_audit_context(request) -> AuditContext:
    """Snapshot request metadata for audit logging (no business logic)."""
    return AuditContext(
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT"),
        endpoint=request.path,
        http_method=request.method,
    )
