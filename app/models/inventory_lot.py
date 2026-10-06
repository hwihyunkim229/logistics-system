from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class InventoryLot(Base):
    __tablename__ = "inventory_lot"
    __table_args__ = (
        UniqueConstraint("inventory_id", "lot", name="uq_inventory_lot_inventory_lot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False, index=True)
    item_code = Column(String, nullable=False, index=True)
    warehouse_type = Column(String, nullable=False)
    grade = Column(String)
    lot = Column(String, nullable=False, index=True)
    first_received_date = Column(Date)
    qty = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now)
