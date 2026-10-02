from datetime import timezone
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def to_kst(value):
    """Convert DB timestamps (stored as UTC, often timezone-naive) to Korea time."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(KST)


def format_kst(value, pattern="%Y-%m-%d %H:%M:%S"):
    converted = to_kst(value)
    return converted.strftime(pattern) if converted else ""
