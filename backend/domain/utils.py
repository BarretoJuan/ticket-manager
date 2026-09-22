"""Small pure-Python helpers shared across the domain layer."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC-aware datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` as a UTC-aware datetime.

    Naive datetimes are assumed to already be in UTC (values must be saved in
    UTC). Aware datetimes are converted to UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
