from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.workflow.models.workflow_notification import WorkflowNotification

def add_notification(
    db: Session,
    workflow_no: str,
    department: str,
    title: str,
    message: str,
    notification_type: str,
):
    notification = WorkflowNotification(
        workflow_no=workflow_no,
        department=department,
        title=title,
        message=message,
        notification_type=notification_type,
    )

    db.add(notification)

    return notification

def get_notifications(
    db: Session,
    department: str = "",
    unread_only: bool = False,
    limit: int = 100,
):
    query = db.query(WorkflowNotification)

    if department:
        query = query.filter(
            WorkflowNotification.department == department
        )

    if unread_only:
        query = query.filter(
            WorkflowNotification.is_read == False
        )

    return (
        query
        .order_by(WorkflowNotification.id.desc())
        .limit(limit)
        .all()
    )

def count_unread(
    db: Session,
    department: str = "",
):
    query = db.query(WorkflowNotification).filter(
        WorkflowNotification.is_read == False
    )

    if department:
        query = query.filter(
            WorkflowNotification.department == department
        )

    return query.count()

def mark_read(
    db: Session,
    notification_id: int,
):
    notification = (
        db.query(WorkflowNotification)
        .filter(WorkflowNotification.id == notification_id)
        .first()
    )

    if notification is None:
        return None

    notification.is_read = True
    notification.read_at = datetime.now(
        ZoneInfo("Asia/Seoul")
    )

    db.commit()

    return notification

def mark_all_read(
    db: Session,
    department: str = "",
):
    query = db.query(WorkflowNotification).filter(
        WorkflowNotification.is_read == False
    )

    if department:
        query = query.filter(
            WorkflowNotification.department == department
        )

    now = datetime.now(ZoneInfo("Asia/Seoul"))

    for notification in query.all():
        notification.is_read = True
        notification.read_at = now

    db.commit()