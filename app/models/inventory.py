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
    # 반제품 / 제품 / 원자재 - only meaningful when warehouse_type == "창고재고"

    warehouse_type = Column(
        String
    )
    # 창고재고 / 제공재고 / 외주재고

    lot = Column(
        String
    )

    grade = Column(
        String
    )
    # A / B / F - only used for warehouse_type == "창고재고"

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
