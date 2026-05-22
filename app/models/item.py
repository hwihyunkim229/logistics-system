from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base
from zoneinfo import ZoneInfo

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    serial = Column(String, unique=True, index=True)
    status = Column(String, default="IN")
    created_at = Column(DateTime, default=datetime.now(ZoneInfo("Asia/Seoul")))