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

class WorkflowInspection(Base):
    __tablename__ = "workflow_inspections"

    id = Column(Integer, primary_key=True)
    workflow_no = Column(String, index=True)
    stage = Column(Integer)
    inspection_type = Column(String)
    inspector = Column(String)
    request_qty = Column(Integer)
    good_qty = Column(Integer, default=0)
    defect_qty = Column(Integer, default=0)
    grade_a_qty = Column(Integer, default=0)
    grade_b_qty = Column(Integer, default=0)
    grade_f_qty = Column(Integer, default=0)
    result = Column(String)
    remark = Column(String)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
    is_completed = Column(
        Boolean,
        default=False
    )
    # 검사 성적서 첨부 - 저장 경로(디스크)와 원본 파일명을 각각
    # 보관한다. 다운로드 시 원본 파일명으로 내려주기 위해 필요하다.
    attachment_path = Column(String)
    attachment_name = Column(String)