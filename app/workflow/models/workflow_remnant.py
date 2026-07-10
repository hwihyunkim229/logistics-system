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
    """잔존 자재 - 단계를 넘어가지 못하고 남은 수량의 기록.

    부분 승인(10개 중 8개만 승인 -> 2개 잔존), 검사 불량, 부분 요청,
    부분 출고 등 수량이 줄어드는 모든 지점에서 생성되며, 잔량이 어느
    부서에 남아 있는지(department)를 기준으로 각 팀 페이지의 잔존
    자재 현황에 표시된다. 해당 단계가 반려되어 재작업되면 그 단계의
    잔존 기록은 삭제되고 재작업 결과로 다시 만들어진다.
    """

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
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            ZoneInfo("Asia/Seoul")
        )
    )
