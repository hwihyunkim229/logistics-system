from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from zoneinfo import ZoneInfo
from datetime import datetime

class Outbound(Base):
    __tablename__ = "outbound"

    id = Column(Integer, primary_key=True)
    serial = Column(String, index=True)
    size = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    product = Column(String)
    category = Column(String)
    client = Column(String)
    note = Column(String)