import os
import re

UPLOAD_DIR = os.path.join("app", "workflow", "uploads", "inspections")

def _safe_filename(name: str) -> str:
    name = os.path.basename(name or "file")
    return re.sub(r"[^\w.\-가-힣 ]", "_", name)[:200] or "file"

def save_inspection_attachment(inspection_id: int, upload) -> tuple:

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