from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from app.database import Base

class WorkflowItem(Base):
    __tablename__ = "workflow_items"

    id = Column(Integer, primary_key=True)
    workflow_no = Column(String, unique=True, index=True)
    item_code = Column(String, index=True)
    item_name = Column(String)
    lot = Column(String)
    rev = Column(String)
    qty = Column(Integer, default=0)
    process_qty = Column(Integer, default=0)
    initial_qty = Column(Integer, default=0)
    received_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    prev_item_code = Column(String)
    prev_item_name = Column(String)
    prev_lot = Column(String)
    merged_into = Column(String)
    current_stage = Column(Integer, default=1)
    status = Column(String, default="IN_PROGRESS")
    current_department = Column(String)
    created_by = Column(String)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        ),
        onupdate=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    service_type = Column(String)