from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base
from zoneinfo import ZoneInfo

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    user = Column(String)
    product = Column(String)
    action = Column(String)
    serial = Column(String)
    detail = Column(String)