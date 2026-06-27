from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class BOM(Base):
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True)
    product_name = Column(String)
    component_code = Column(String)
    component_name = Column(String)
    qty = Column(Float)