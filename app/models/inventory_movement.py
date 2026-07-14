from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime
)
from datetime import datetime
from app.database import Base

class InventoryMovement(Base):

    __tablename__ = "inventory_movement"

    id = Column(Integer, primary_key=True)
    item_code = Column(String)
    item_name = Column(String)
    category = Column(String)
    warehouse_type = Column(String)
    movement_type = Column(String)
    qty = Column(Integer)
    user = Column(String)
    source = Column(String)
    created_at = Column(
        DateTime,
        default=datetime.now
    )