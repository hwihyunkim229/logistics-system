from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base
from zoneinfo import ZoneInfo

class Movement(Base):
    __tablename__ = "movement"

    id = Column(Integer, primary_key=True)
    serial = Column(String, index=True)
    product = Column(String, index=True)
    type = Column(String, index=True)
    source = Column(String)
    client = Column(String, nullable=True)
    category = Column(String, nullable=True)
    user = Column(String, nullable=True)

    def korea_time():
        return datetime.now(
            ZoneInfo("Asia/Seoul")
        )

    created_at = Column(DateTime(timezone=True), default=korea_time, index=True)