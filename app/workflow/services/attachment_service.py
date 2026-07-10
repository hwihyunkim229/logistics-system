import os
import re

UPLOAD_DIR = os.path.join("app", "workflow", "uploads", "inspections")


def _safe_filename(name: str) -> str:
    name = os.path.basename(name or "file")
    return re.sub(r"[^\w.\-가-힣 ]", "_", name)[:200] or "file"


def save_inspection_attachment(inspection_id: int, upload) -> tuple:
    """
    업로드된 검사 성적서 파일을 디스크에 저장하고
    (저장 경로, 원본 파일명)을 반환한다.
    """

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_name = _safe_filename(upload.filename)
    stored_path = os.path.join(
        UPLOAD_DIR, f"{inspection_id}__{safe_name}"
    )

    with open(stored_path, "wb") as f:
        f.write(upload.file.read())

    return stored_path, upload.filename


def delete_inspection_attachment(path: str):
    if path and os.path.exists(path):
        os.remove(path)
