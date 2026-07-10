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
    # 최초 입고 수량 - qty는 단계가 진행되며 승인/검사 결과로 줄어들기
    # 때문에, 원래 얼마나 들어왔는지는 별도로 보존해야 잔량을 계산하고
    # 표시할 수 있다.
    initial_qty = Column(Integer, default=0)
    # 입고 일자 - 기본은 등록 시각이지만 구매팀이 실제 입고일로 수정할
    # 수 있다 (created_at은 시스템 기록용이라 건드리지 않는다).
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