from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from app.utils.logger import save_log
from app.database import SessionLocal
from app.models.user import User
from app.models.activity_log import ActivityLog
from fastapi.responses import FileResponse
import shutil
import os
from datetime import datetime, timedelta
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from zoneinfo import ZoneInfo

router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

@router.get(
    "/admin/users",
    response_class=HTMLResponse
)
def admin_users(request: Request):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db = SessionLocal()

    users = db.query(User).all()

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "users": users,
            "current_user": request.session.get("user")
        }
    )

@router.post("/admin/create-user")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    team: str = Form("")
):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db = SessionLocal()

    exists = db.query(User).filter(
        User.username == username
    ).first()

    if exists:

        db.close()

        return RedirectResponse(
            "/admin/users",
            status_code=303
        )

    hashed_password = pwd_context.hash(
        password
    )

    # admin은 팀 제한을 두지 않는다 - 팀은 실무자(user) 계정 전용.
    if role == "admin":
        team = ""

    user = User(
        username=username,
        password=hashed_password,
        role=role,
        team=team,
        must_change_password=True
    )

    db.add(user)

    db.commit()

    save_log(
        user=request.session.get("user"),
        product="ADMIN",
        action="CREATE_USER",
        serial=username,
        detail="계정 생성"
    )

    db.close()

    return RedirectResponse(
        "/admin/users",
        status_code=303
    )

@router.post("/admin/reset-password/{user_id}")
def reset_password(
    request: Request,
    user_id: int
):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db = SessionLocal()

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user:

        user.password = pwd_context.hash(
            "1234"
        )

        user.must_change_password = True

        db.commit()

    save_log(
        user=request.session.get("user"),
        product="ADMIN",
        action="RESET_PASSWORD",
        serial=user.username,
        detail="비밀번호 초기화"
    )

    db.close()

    return RedirectResponse(
        "/admin/users",
        status_code=303
    )

@router.post("/admin/delete-user/{user_id}")
def delete_user(
    request: Request,
    user_id: int
):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db = SessionLocal()

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    current_user = request.session.get(
        "user"
    )

    if user and user.username != current_user:

        db.delete(user)

        db.commit()

        save_log(
            user=request.session.get("user"),
            product="ADMIN",
            action="DELETE_USER",
            serial=user.username,
            detail="계정 삭제"
        )


    db.close()

    return RedirectResponse(
        "/admin/users",
        status_code=303
    )

@router.get("/admin/activity")
def admin_activity(
    request: Request
):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db = SessionLocal()

    query = db.query(ActivityLog)

    start_date = request.query_params.get(
        "start_date"
    )

    end_date = request.query_params.get(
        "end_date"
    )

    if start_date:

        start_dt = datetime.combine(
            datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date(),
            datetime.min.time()
        )

        query = query.filter(
            ActivityLog.created_at >= start_dt
        )

    if end_date:

        end_dt = datetime.combine(
            datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date(),
            datetime.max.time()
        )

        query = query.filter(
            ActivityLog.created_at <= end_dt
        )

    user = request.query_params.get("user")

    action = request.query_params.get(
        "action"
    )

    serial = request.query_params.get(
        "serial"
    )

    page = int(
        request.query_params.get(
            "page",
            1
        )
    )

    per_page = 30

    if user:

        query = query.filter(
            ActivityLog.user.contains(user)
        )

    if action:

        query = query.filter(
            ActivityLog.action == action
        )

    if serial:

        query = query.filter(
            ActivityLog.serial.contains(serial)
        )

    total_count = query.count()

    total_pages = (
        total_count + per_page - 1
    ) // per_page

    logs = (
        query
        .order_by(ActivityLog.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    base_actions = [
        "LOGIN",
        "LOGOUT",
        "UPLOAD_EXCEL",
        "DOWNLOAD_EXCEL",
        "OUTBOUND",
        "INBOUND",
        "MOVE_IN",
        "MOVE_OUT",
        "DELETE_SELECTED",
        "DELETE_ALL",
        "BULK_UPDATE",
        "UPDATE_FIELD",
        "UPDATE_SIZE",
        "CREATE_USER",
        "RESET_PASSWORD",
        "DELETE_USER",
        "CHANGE_PASSWORD",
        "STOCK_MOVE_IN",
        "STOCK_MOVE_OUT",
        "STOCK_DELETE_SELECTED",
        "STOCK_DOWNLOAD_EXCEL",
        "STOCK_UPLOAD_EXCEL",
        "STOCK_UPDATE_QTY",
        "STOCK_UPDATE_GRADE",
        "STOCK_BULK_UPDATE_GRADE",
        "STOCK_BULK_UPDATE_QTY",
        "STOCK_HISTORY_DOWNLOAD_EXCEL",
        "STOCK_ITEM_MASTER_UPDATE",
        "STOCK_ITEM_MASTER_UPLOAD",
        "MRP_BOM_UPLOAD",
        "MRP_BOM_DOWNLOAD",
        "MRP_PRODUCTION_PLAN_UPLOAD",
        "MRP_PRODUCTION_PLAN_DOWNLOAD",
        "MRP_RESULT_DOWNLOAD",
        "MRP_MATERIAL_MASTER_ADD",
        "MRP_MATERIAL_MASTER_UPDATE",
        "MRP_MATERIAL_MASTER_UPLOAD",
        "MRP_MATERIAL_MASTER_DOWNLOAD",
        "MRP_MATERIAL_NOTE_SAVE",
        "INVENTORY_ADD",
        "INVENTORY_MOVE_IN",
        "INVENTORY_MOVE_OUT",
        "INVENTORY_DELETE_SELECTED",
        "INVENTORY_UPDATE_FIELD",
        "INVENTORY_BULK_UPDATE_QTY",
        "INVENTORY_BULK_UPDATE_NOTE",
        "INVENTORY_BULK_UPDATE_LOT",
        "INVENTORY_HISTORY_DOWNLOAD_EXCEL",
        "INVENTORY_DOWNLOAD_EXCEL",
        "INVENTORY_UPLOAD_EXCEL",
    ]

    existing_actions = [
        row[0]
        for row in db.query(ActivityLog.action)
        .distinct()
        .order_by(ActivityLog.action)
        .all()
        if row[0]
    ]

    ACTIONS = sorted(
        set(base_actions + existing_actions)
    )

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/activity.html",
        context={
            "logs": logs,
            "actions": ACTIONS,
            "selected_action": action,
            "search_user": user,
            "search_serial": serial,
            "page": page,
            "total_pages": total_pages,
            "start_date": start_date,
            "end_date": end_date
        }
    )

@router.get("/admin/backup-db")
def backup_db(request: Request):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db_path = "logistics.db"

    timestamp = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_name = (
        f"backup_{timestamp}.db"
    )

    backup_path = os.path.join(
        "backups",
        backup_name
    )

    os.makedirs(
        "backups",
        exist_ok=True
    )

    shutil.copy(
        db_path,
        backup_path
    )

    return FileResponse(
        path=backup_path,
        filename=backup_name,
        media_type="application/octet-stream"
    )

@router.get("/admin/activity-export")
def export_activity_excel(
    request: Request
):

    if request.session.get("role") != "admin":

        return RedirectResponse(
            "/search",
            status_code=303
        )

    db = SessionLocal()

    logs = db.query(ActivityLog)\
        .order_by(ActivityLog.id.desc())\
        .all()

    rows = []

    for log in logs:

        rows.append({
            "Product": log.product,
            "시간": log.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "사용자": log.user,
            "작업": log.action,
            "Serial": log.serial,
            "작업 내용": log.detail
        })

    df = pd.DataFrame(rows)

    output = io.BytesIO()

    df.to_excel(
        output,
        index=False
    )

    output.seek(0)

    db.close()

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            "attachment; filename=activity_logs.xlsx"
        }
    )
