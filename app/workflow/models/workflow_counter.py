from sqlalchemy import Column, String, Integer
from app.database import Base


class WorkflowCounter(Base):
    """
    workflow_no 발급용 전역 시퀀스. WorkflowItem.id로 workflow_no를
    만들면, 행이 삭제된 뒤 SQLite가 그 id를 재사용할 때 완전히 다른
    품목이 예전과 똑같은 workflow_no를 갖게 되는 문제가 있다 - 이
    카운터는 WorkflowItem 행 삭제/재사용과 무관하게 계속 증가만
    하므로 그런 충돌이 생기지 않는다.
    """

    __tablename__ = "workflow_counters"

    key = Column(String, primary_key=True)
    value = Column(Integer, default=0)