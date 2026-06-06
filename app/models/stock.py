from sqlalchemy import Column, Integer, String
from app.database import Base

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True)
    item_code = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    grade = Column(String)
    rev = Column(String)
    category = Column(String, nullable=False)
    qty = Column(Integer, default=0)