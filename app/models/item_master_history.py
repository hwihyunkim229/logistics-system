from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime
)
from datetime import datetime
from app.database import Base

class ItemMasterHistory(Base):

    __tablename__ = "item_master_history"

    id = Column(Integer, primary_key=True)

    old_code = Column(String)
    new_code = Column(String)

    old_name = Column(String)
    new_name = Column(String)

    old_rev = Column(String)
    new_rev = Column(String)

    user = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.now
    )