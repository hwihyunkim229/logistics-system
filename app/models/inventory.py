from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from app.database import Base

class Inventory(Base):

    __tablename__ = "inventory"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    item_code = Column(
        String,
        index=True
    )

    item_name = Column(
        String
    )

    category = Column(
        String
    )

    warehouse_type = Column(
        String
    )

    lot = Column(
        String
    )

    grade = Column(
        String
    )

    rev = Column(
        String
    )

    note = Column(
        String
    )

    qty = Column(
        Integer,
        default=0
    )