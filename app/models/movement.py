from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timedelta
from app.database import Base

class Movement(Base):
    __tablename__ = "movement"

    id = Column(Integer, primary_key=True)
    serial = Column(String, index=True)
    product = Column(String)

    type = Column(String)
    source = Column(String)

    client = Column(String, nullable=True)
    category = Column(String, nullable=True)
    user = Column(String, nullable=True)

    def korea_time():
        return datetime.utcnow() + timedelta(hours=9)

    created_at = Column(DateTime, default=korea_time)