from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def to_kst(value):
    """Return a timestamp in Korea time.

    Legacy movement tables store Korea-local wall-clock values in timezone-naive
    columns.  Attaching UTC to those values shifts the displayed time by nine
    hours, so naive values must be interpreted as KST.  Timezone-aware values
    are converted normally.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def format_kst(value, pattern="%Y-%m-%d %H:%M:%S"):
    converted = to_kst(value)
    return converted.strftime(pattern) if converted else ""
