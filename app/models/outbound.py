from sqlalchemy import Column, Integer, String, Date
from datetime import date
from app.database import Base

class Outbound(Base):
    __tablename__ = "outbound"

    id = Column(Integer, primary_key=True)
    serial = Column(String, index=True)
    size = Column(String, nullable=True)
    created_at = Column(Date, default=date.today)
    product = Column(String)
    category = Column(String)
    client = Column(String)
    note = Column(String)