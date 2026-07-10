from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String, default="user")
    # 소속 팀 (purchase/quality/material/production). 빈 값이면 팀
    # 제한 없는 일반 계정. 팀 계정은 통합 워크플로우에서 자기 팀
    # 페이지만 수정할 수 있고 나머지 메뉴는 뷰어(조회 전용)가 된다.
    team = Column(String, default="")
    must_change_password = Column(
        Boolean,
        default=True
    )