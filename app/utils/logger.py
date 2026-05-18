from app.database import SessionLocal
from app.models.activity_log import ActivityLog


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
        detail=detail
    )

    db.add(log)

    db.commit()

    db.close()