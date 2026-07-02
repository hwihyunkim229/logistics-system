from datetime import datetime
from sqlalchemy import func

from app.models.user import User
from app.models.activity_log import ActivityLog


class LogisticsAssistant:

    def __init__(self, db):

        self.db = db

    def ask(self, question: str):

        q = question.strip().lower()

        if (
            "사용자 수" in q
            or "계정 수" in q
            or "유저 수" in q
        ):

            return self.user_count()

        if (
            "관리자" in q
            and "몇" in q
        ):

            return self.admin_count()

        if (
            "일반 사용자" in q
            or "user 계정" in q
        ):

            return self.normal_user_count()

        if (
            "비밀번호" in q
            and "변경" in q
        ):

            return self.must_change_password()

        if (
            "오늘 로그인" in q
        ):

            return self.today_login()

        if (
            "최근 작업" in q
            or "최근 로그" in q
        ):

            return self.recent_activity()

        if (
            "활동 로그" in q
        ):

            return {
                "type":"move",
                "url":"/admin/activity",
                "message":"활동 로그 화면으로 이동합니다."
            }

        if (
            "사용자 관리" in q
        ):

            return {
                "type":"move",
                "url":"/admin/users",
                "message":"사용자 관리 화면으로 이동합니다."
            }

        if "dashboard" in question:
            return {
                "type": "move",
                "url": "/dashboard",
                "message": "Dashboard 화면으로 이동합니다."
            }

        if "재고" in question:
            return {
                "type": "move",
                "url": "/stock",
                "message": "재고 현황 화면으로 이동합니다."
            }

        if "bom" in question:
            return {
                "type": "move",
                "url": "/mrp/bom",
                "message": "BOM 화면으로 이동합니다."
            }

        if "생산" in question:
            return {
                "type": "move",
                "url": "/mrp/production-plan",
                "message": "생산 계획 화면으로 이동합니다."
            }

        if "mrp" in question:
            return {
                "type": "move",
                "url": "/bom/dashboard",
                "message": "MRP Dashboard로 이동합니다."
            }

        if "품목" in question:
            return {
                "type": "move",
                "url": "/item-master",
                "message": "품목 관리 화면으로 이동합니다."
            }

        return {
            "type": "text",
            "message": "죄송합니다. 아직 지원하지 않는 질문입니다."
        }
    
    def user_count(self):

        count = self.db.query(User).count()

        return {
            "type":"text",
            "message":f"현재 등록된 사용자는 {count}명입니다."
        }
    
    def admin_count(self):

        count = (
            self.db.query(User)
            .filter(User.role=="admin")
            .count()
        )

        return {
            "type":"text",
            "message":f"관리자 계정은 {count}명입니다."
        }
    
    def normal_user_count(self):

        count = (
            self.db.query(User)
            .filter(User.role=="user")
            .count()
        )

        return {
            "type":"text",
            "message":f"일반 사용자 계정은 {count}명입니다."
        }
    
    def must_change_password(self):

        users = (
            self.db.query(User)
            .filter(User.must_change_password == True)
            .all()
        )

        if not users:

            return {
                "type":"text",
                "message":"모든 사용자가 비밀번호를 변경했습니다."
            }

        names = "\n".join(
            user.username
            for user in users
        )

        return {
            "type":"text",
            "message":
            f"비밀번호 변경이 필요한 사용자는 {len(users)}명입니다.\n\n{names}"
        }
    
    def today_login(self):

        today = datetime.now().date()

        count = (
            self.db.query(ActivityLog)
            .filter(
                func.date(ActivityLog.created_at) == today
            )
            .filter(
                ActivityLog.action == "LOGIN"
            )
            .count()
        )

        return {
            "type":"text",
            "message":f"오늘 로그인은 {count}건입니다."
        }
    
    def recent_activity(self):

        logs = (
            self.db.query(ActivityLog)
            .order_by(ActivityLog.id.desc())
            .limit(5)
            .all()
        )

        if not logs:

            return {
                "type":"text",
                "message":"작업 이력이 없습니다."
            }

        text = "최근 작업입니다.\n\n"

        for log in logs:

            text += (
                f"{log.created_at.strftime('%m-%d %H:%M')} "
                f"{log.user} "
                f"{log.action}\n"
            )

        return {
            "type":"text",
            "message":text
        }