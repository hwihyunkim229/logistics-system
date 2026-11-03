from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class StockLot(Base):
    __tablename__ = "stock_lot"
    __table_args__ = (
        UniqueConstraint("stock_id", "lot", name="uq_stock_lot_stock_lot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stock.id"), nullable=False, index=True)
    item_code = Column(String, nullable=False, index=True)
    grade = Column(String)
    lot = Column(String, nullable=False, index=True)
    first_received_date = Column(Date)
    inspector = Column(String)
    qty = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now)
