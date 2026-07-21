from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

def dated_filename(label: str, extension: str = "xlsx") -> str:
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    safe_label = "".join(
        "_" if character in '\\/:*?\"<>|' else character
        for character in label.strip()
    )
    return f"{safe_label}_{today}.{extension}"

def download_content_disposition(
    label: str,
    fallback: str = "download",
    extension: str = "xlsx",
) -> str:
    korean_filename = dated_filename(label, extension)
    fallback_filename = dated_filename(fallback, extension)
    encoded_filename = quote(korean_filename)
    return (
        f'attachment; filename="{fallback_filename}"; '
        f"filename*=UTF-8''{encoded_filename}"
    )