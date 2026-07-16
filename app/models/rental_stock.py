from sqlalchemy import Column, Integer, String
from app.database import Base

class RentalStock(Base):
    __tablename__ = "rental_stock"
    id = Column(Integer, primary_key=True)
    item_code = Column(String, nullable=False, index=True)
    item_name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    qty = Column(Integer, nullable=False, default=0)
