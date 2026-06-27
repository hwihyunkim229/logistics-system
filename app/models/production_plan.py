from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Date

from datetime import datetime

from app.database import Base


class ProductionPlan(Base):

    __tablename__ = "production_plan"

    id = Column(Integer, primary_key=True)

    plan_date = Column(Date)

    product_name = Column(String)

    plan_qty = Column(Integer)