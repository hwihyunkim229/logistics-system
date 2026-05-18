from sqlalchemy import Column, Integer, String, Date
from app.database import Base

class Inbound(Base):
    __tablename__ = "inbound"

    id = Column(Integer, primary_key=True)
    serial = Column(String, index=True)
    size = Column(String)
    created_at = Column(Date)
    product = Column(String)
    category = Column(String)
    client = Column(String)
    note = Column(String)