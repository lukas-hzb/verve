"""UTC time helpers for the application's timezone-naive database schema."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time without tzinfo for legacy DB compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)
