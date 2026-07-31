from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base

class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Seoul")),
        nullable=False,
        index=True,
    )
    user = Column(String, nullable=False, default="anonymous", index=True)
    ip_address = Column(String, nullable=False, default="")
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    result = Column(String(30), nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    detail = Column(Text, nullable=False, default="")
    user_agent = Column(String(500), nullable=False, default="")