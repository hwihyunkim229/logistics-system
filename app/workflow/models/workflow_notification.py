from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from app.database import Base

class WorkflowNotification(Base):
    __tablename__ = "workflow_notifications"

    id = Column(Integer, primary_key=True)
    workflow_no = Column(String, index=True)
    department = Column(String)
    user_name = Column(String)
    title = Column(String)
    message = Column(String)
    notification_type = Column(String)
    is_read = Column(
        Boolean,
        default=False
    )
    read_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )