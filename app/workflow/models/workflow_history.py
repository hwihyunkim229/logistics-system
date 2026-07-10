from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from app.database import Base

class WorkflowHistory(Base):
    __tablename__ = "workflow_histories"

    id = Column(Integer, primary_key=True)
    workflow_no = Column(String, index=True)
    stage = Column(Integer)
    action = Column(String)
    user_name = Column(String)
    department = Column(String)
    before_qty = Column(Integer)
    after_qty = Column(Integer)
    remark = Column(String)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    result = Column(String)