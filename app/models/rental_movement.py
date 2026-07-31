from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, Integer, String
from app.database import Base

class RentalMovement(Base):
    __tablename__ = "rental_movement"
    id = Column(Integer, primary_key=True)
    movement_type = Column(String, nullable=False, default="OUT")
    item_code = Column(String, nullable=False, index=True)
    item_name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    qty = Column(Integer, nullable=False, default=1)
    headquarters = Column(String, nullable=False)
    department = Column(String, nullable=False)
    requester = Column(String, nullable=False)
    size = Column(String, nullable=False)
    serial_number = Column(String, nullable=False)
    issue_date = Column(Date, nullable=False, default=date.today, index=True)
    remark = Column(String, default="")
    user = Column(String, default="system")
    created_at = Column(DateTime, default=datetime.now)