from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from app.database import Base
from sqlalchemy import Boolean

class WorkflowRequest(Base):
    __tablename__ = "workflow_requests"

    id = Column(Integer, primary_key=True)
    workflow_no = Column(String, index=True)
    stage = Column(Integer)
    from_department = Column(String)
    to_department = Column(String)
    request_qty = Column(Integer)
    approved_qty = Column(Integer, default=0)
    requested_by = Column(String)
    approved_by = Column(String)
    request_type = Column(String)
    status = Column(
        String,
        default="WAITING"
    )
    requested_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    remark = Column(String)
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
    physical_checked = Column(
        Boolean,
        default=False
    )
    service_type = Column(String)
    item_code = Column(String)
    item_name = Column(String)