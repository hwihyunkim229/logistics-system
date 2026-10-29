from datetime import datetime, timezone
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc


def utc_now_naive():
    """Return the canonical DB timestamp: UTC without tzinfo."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_kst(value):
    """Return a timestamp in Korea time.

    Movement timestamps are stored as UTC in timezone-naive database columns.
    Interpret naive values as UTC, then convert them for display in Korea.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(KST)


def kst_to_utc_naive(value):
    """Convert a naive Korea-local datetime to the UTC-naive DB convention."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    return value.astimezone(UTC).replace(tzinfo=None)


def format_kst(value, pattern="%Y-%m-%d %H:%M:%S"):
    converted = to_kst(value)
    return converted.strftime(pattern) if converted else ""
