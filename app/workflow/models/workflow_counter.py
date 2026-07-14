from sqlalchemy import Column, String, Integer
from app.database import Base

class WorkflowCounter(Base):
    __tablename__ = "workflow_counters"

    key = Column(String, primary_key=True)
    value = Column(Integer, default=0)