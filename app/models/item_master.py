from sqlalchemy import Column, Integer, String
from app.database import Base

class ItemMaster(Base):
    __tablename__ = "item_master"

    id = Column(Integer, primary_key=True)

    item_code = Column(String, unique=True, index=True)
    item_name = Column(String)
    rev = Column(String)