from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from app.database import Base

class WorkflowRemnant(Base):
    __tablename__ = "workflow_remnants"

    id = Column(Integer, primary_key=True)
    workflow_no = Column(String, index=True)
    stage = Column(Integer)
    department = Column(String, index=True)
    item_code = Column(String)
    item_name = Column(String)
    lot = Column(String)
    qty = Column(Integer, default=0)
    reason = Column(String)
    source_warehouse = Column(String)
    transfer_status = Column(String, default="AVAILABLE")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )