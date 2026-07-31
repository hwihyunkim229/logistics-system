from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class UserPermission(Base):
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "feature",
            "action",
            name="uq_user_permission_feature_action",
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    allowed = Column(Boolean, nullable=False, default=False)
