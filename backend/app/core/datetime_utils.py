"""UTC datetime helpers: MySQL often returns naive datetimes (stored as UTC)."""

from datetime import datetime, timezone


def to_utc_aware(dt: datetime | None) -> datetime | None:
    """Interpret naive values as UTC; normalize aware values to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def naive_utc(dt: datetime) -> datetime:
    """Store instants as naive UTC (common for MySQL DATETIME columns)."""
    return to_utc_aware(dt).replace(tzinfo=None)
