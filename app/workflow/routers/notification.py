from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from threading import Lock
from time import monotonic
from app.workflow.utils import get_db, department_name
from app.workflow.services.notification_service import (
    get_notifications,
    count_unread,
    mark_read,
    mark_all_read,
)
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_stage import WorkflowStage

router = APIRouter(
    prefix="/workflow/notification",
    tags=["Workflow Notification"],
)

templates = Jinja2Templates(
    directory="app/templates"
)

TODO_CACHE_SECONDS = 30
_todo_cache = {"expires_at": 0.0, "todos": None}
_todo_cache_lock = Lock()

@router.get("")
def notification_page(
    request: Request,
    department: str = "",
    unread: str = "",
    db: Session = Depends(get_db),
):
    notifications = get_notifications(
        db,
        department=department.strip(),
        unread_only=unread == "1",
        limit=200,
    )

    for row in notifications:
        row.department_label = department_name(row.department)

    return templates.TemplateResponse(
        request,
        "workflow/notification.html",
        {
            "notifications": notifications,
            "department": department,
            "unread": unread,
            "unread_count": count_unread(db, department.strip()),
            "total_count": len(notifications),
        },
    )

@router.get("/todo")
def todo(
    request: Request,
    db: Session = Depends(get_db),
):
    now = monotonic()

    with _todo_cache_lock:
        todos = _todo_cache["todos"]

        if todos is None or now >= _todo_cache["expires_at"]:
            item_rows = (
                db.query(
                    WorkflowItem.current_stage,
                    func.count(WorkflowItem.id),
                    func.coalesce(func.sum(WorkflowItem.qty), 0),
                )
                .filter(WorkflowItem.status == "IN_PROGRESS")
                .group_by(WorkflowItem.current_stage)
                .all()
            )
            request_rows = (
                db.query(
                    WorkflowRequest.stage,
                    func.count(WorkflowRequest.id),
                    func.coalesce(func.sum(WorkflowRequest.request_qty), 0),
                )
                .filter(WorkflowRequest.status == "WAITING")
                .group_by(WorkflowRequest.stage)
                .all()
            )

            item_stats = {
                int(stage): (int(count), int(qty or 0))
                for stage, count, qty in item_rows
            }
            request_stats = {
                int(stage): (int(count), int(qty or 0))
                for stage, count, qty in request_rows
            }

            todos = {
                "purchase": [],
                "quality": [],
                "material": [],
                "production": [],
            }

            def _stats(source, *stages):
                values = [
                    source.get(int(stage), (0, 0))
                    for stage in stages
                ]
                return (
                    sum(value[0] for value in values),
                    sum(value[1] for value in values),
                )

            def _add(team, label, stats):
                count, qty = stats
                if count:
                    todos[team].append({
                        "label": label,
                        "count": count,
                        "qty": qty,
                        "link": f"/workflow/{team}",
                    })

            _add("purchase", "입고 검사 의뢰 필요", _stats(
                item_stats, WorkflowStage.PURCHASE_RECEIVED
            ))
            _add("quality", "입고 검사 승인 대기", _stats(
                request_stats, WorkflowStage.QUALITY_REQUEST
            ))
            _add("quality", "입고 검사 진행 필요", _stats(
                item_stats, WorkflowStage.QUALITY_APPROVAL
            ))
            _add("quality", "공정 검사 진행 필요", _stats(
                item_stats, WorkflowStage.PROCESS_INSPECTION_REQUEST
            ))
            _add("material", "확인/승인 필요", _stats(
                item_stats,
                WorkflowStage.QUALITY_INSPECTION,
                WorkflowStage.PRODUCTION_COMPLETE,
                WorkflowStage.PROCESS_INSPECTION,
                WorkflowStage.PACKAGING_COMPLETE,
            ))
            _add("material", "다음 단계 요청 필요", _stats(
                item_stats,
                WorkflowStage.MATERIAL_CONFIRM_1,
                WorkflowStage.MATERIAL_CONFIRM_2,
                WorkflowStage.MATERIAL_CONFIRM_3,
            ))
            _add("material", "제품 출고 대기", _stats(
                item_stats, WorkflowStage.MATERIAL_FINAL_CONFIRM
            ))
            _add("production", "생산 승인 대기", _stats(
                request_stats, WorkflowStage.PRODUCTION_REQUEST
            ))
            _add("production", "생산 완료 등록 필요", _stats(
                item_stats, WorkflowStage.PRODUCTION_APPROVAL
            ))
            _add("production", "포장 완료 등록 필요", _stats(
                item_stats, WorkflowStage.PACKAGING_REQUEST
            ))

            _todo_cache["todos"] = todos
            _todo_cache["expires_at"] = now + TODO_CACHE_SECONDS

    team = request.session.get("team") or ""

    if team and request.session.get("role") != "admin":
        visible = {team: todos.get(team, [])}
    else:
        visible = todos

    result = []

    for team_code, entries in visible.items():
        for entry in entries:
            result.append({
                **entry,
                "team": team_code,
                "team_name": department_name(team_code),
            })

    return JSONResponse({
        "total": sum(e["count"] for e in result),
        "items": result,
    })

@router.post("/read")
def read_notification(
    notification_id: int = Form(...),
    db: Session = Depends(get_db),
):
    mark_read(db, notification_id)

    return RedirectResponse(
        "/workflow/notification",
        status_code=303,
    )

@router.post("/read-all")
def read_all_notifications(
    department: str = Form(""),
    db: Session = Depends(get_db),
):
    mark_all_read(db, department)

    return RedirectResponse(
        "/workflow/notification",
        status_code=303,
    )