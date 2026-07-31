from sqlalchemy import Column, Integer, String
from app.database import Base

class RentalCategory(Base):
    __tablename__ = "rental_category"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)