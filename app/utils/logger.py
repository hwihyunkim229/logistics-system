from app.database import SessionLocal
from app.models.activity_log import ActivityLog
from datetime import datetime
from zoneinfo import ZoneInfo

def save_log(
    *,
    user,
    product,
    action,
    serial="",
    detail=""
):

    db = SessionLocal()

    log = ActivityLog(
        user=user,
        product=product,
        action=action,
        serial=serial,
        detail=detail,
        created_at=datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )

    db.add(log)

    db.commit()

    db.close()