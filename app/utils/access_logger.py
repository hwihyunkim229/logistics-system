from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.models.access_log import AccessLog


KST = ZoneInfo("Asia/Seoul")
ACCESS_LOG_RETENTION_DAYS = 180
_cleanup_lock = Lock()
_last_cleanup_date = None


IGNORED_PATHS = {
    "/health",
    "/favicon.ico",
    "/workflow/notification/todo",
}

PAGE_ACTIONS = {
    "/search": "통합 검색 조회",
    "/stock": "재고 조회",
    "/stock/history": "재고 이력 조회",
    "/stock/dashboard": "재고 현황 조회",
    "/stock/item-master/manage": "품목 마스터 조회",
    "/inventory": "시리얼 재고 조회",
    "/inventory/history": "시리얼 재고 이력 조회",
    "/inventory/dashboard": "시리얼 재고 현황 조회",
    "/rental": "대여 재고 조회",
    "/rental/history": "대여 이력 조회",
    "/mrp/result": "MRP 결과 조회",
    "/mrp/material-master": "자재 마스터 조회",
    "/admin/activity": "업무 로그 조회",
    "/admin/access": "접근 감사 로그 조회",
    "/admin/users": "사용자 관리 조회",
}


def cleanup_expired_access_logs():
    global _last_cleanup_date

    today = datetime.now(KST).date()
    if _last_cleanup_date == today:
        return

    with _cleanup_lock:
        if _last_cleanup_date == today:
            return

        db = SessionLocal()
        try:
            cutoff = datetime.now(KST) - timedelta(
                days=ACCESS_LOG_RETENTION_DAYS
            )
            (
                db.query(AccessLog)
                .filter(AccessLog.created_at < cutoff)
                .delete(synchronize_session=False)
            )
            db.commit()
            _last_cleanup_date = today
        except Exception:
            db.rollback()
        finally:
            db.close()


def client_ip(request):
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()

    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else ""


def should_record(path):
    return (
        path not in IGNORED_PATHS
        and not path.startswith("/static/")
        and not path.startswith("/workflow/static/")
    )


def describe_action(method, path):
    if path in PAGE_ACTIONS and method == "GET":
        return PAGE_ACTIONS[path]

    lowered = path.lower()

    if "download" in lowered or "export" in lowered:
        return "파일 다운로드"
    if "upload" in lowered:
        return "파일 업로드"
    if path == "/logout":
        return "로그아웃"
    if method == "GET":
        return "화면/데이터 조회"
    if method == "POST":
        return "데이터 등록/처리"
    if method in {"PUT", "PATCH"}:
        return "데이터 수정"
    if method == "DELETE":
        return "데이터 삭제"
    return f"{method} 요청"


def result_from_status(status_code):
    if status_code < 300:
        return "성공"
    if status_code < 400:
        return "이동/인증필요"
    if status_code == 401:
        return "인증실패"
    if status_code == 403:
        return "권한없음"
    if status_code == 409:
        return "충돌/중복"
    if status_code == 429:
        return "요청제한"
    return "실패"


def save_access_log(
    *,
    request,
    status_code,
    user=None,
    action=None,
    result=None,
    detail="",
):
    path = request.url.path
    if not should_record(path):
        return

    query = unquote(request.url.query)
    requested_path = path + (f"?{query}" if query else "")
    username = user or request.session.get("user") or "anonymous"

    cleanup_expired_access_logs()

    db = SessionLocal()
    try:
        db.add(
            AccessLog(
                user=str(username)[:200],
                ip_address=client_ip(request)[:100],
                method=request.method[:10],
                path=requested_path[:500],
                action=(action or describe_action(request.method, path))[:100],
                result=(result or result_from_status(status_code))[:30],
                status_code=status_code,
                detail=detail[:2000],
                user_agent=request.headers.get("user-agent", "")[:500],
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
