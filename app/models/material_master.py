from sqlalchemy import Column, Integer, String
from app.database import Base


class MaterialMaster(Base):

    __tablename__ = "material_master"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    item_code = Column(
        String,
        unique=True,
        nullable=False
    )

    item_name = Column(
        String,
        nullable=False
    )

    supplier = Column(
        String,
        default=""
    )

    lead_time_week = Column(
        Integer,
        default=0
    )

    moq = Column(
        Integer,
        default=0
    )