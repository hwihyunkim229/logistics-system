from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

class MaterialNote(Base):

    __tablename__ = "material_note"

    id = Column(
        Integer,
        primary_key=True
    )

    item_code = Column(
        String,
        nullable=False,
        unique=True
    )

    note = Column(
        Text
    )

    created_at = Column(
        DateTime,
        default=datetime.now
    )

    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now
    )