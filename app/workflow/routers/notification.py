from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
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
    def _stage_items(*stages):
        return (
            db.query(WorkflowItem)
            .filter(
                WorkflowItem.current_stage.in_([int(s) for s in stages]),
                WorkflowItem.status == "IN_PROGRESS",
            )
            .all()
        )

    def _waiting_requests(stage):
        return (
            db.query(WorkflowRequest)
            .filter(
                WorkflowRequest.stage == int(stage),
                WorkflowRequest.status == "WAITING",
            )
            .all()
        )

    todos = {
        "purchase": [],
        "quality": [],
        "material": [],
        "production": [],
    }

    def _add(team, label, rows, qty):
        if rows:
            todos[team].append({
                "label": label,
                "count": len(rows),
                "qty": qty,
                "link": f"/workflow/{team}",
            })

    rows = _stage_items(WorkflowStage.PURCHASE_RECEIVED)
    _add("purchase", "입고 검사 의뢰 필요", rows,
         sum(i.qty or 0 for i in rows))

    reqs = _waiting_requests(WorkflowStage.QUALITY_REQUEST)
    _add("quality", "입고 검사 승인 대기", reqs,
         sum(r.request_qty or 0 for r in reqs))

    rows = _stage_items(WorkflowStage.QUALITY_APPROVAL)
    _add("quality", "입고 검사 진행 필요", rows,
         sum(i.qty or 0 for i in rows))

    rows = _stage_items(WorkflowStage.PROCESS_INSPECTION_REQUEST)
    _add("quality", "공정 검사 진행 필요", rows,
         sum(i.qty or 0 for i in rows))

    rows = _stage_items(
        WorkflowStage.QUALITY_INSPECTION,
        WorkflowStage.PRODUCTION_COMPLETE,
        WorkflowStage.PROCESS_INSPECTION,
        WorkflowStage.PACKAGING_COMPLETE,
    )
    _add("material", "확인/승인 필요", rows,
         sum(i.qty or 0 for i in rows))

    rows = _stage_items(
        WorkflowStage.MATERIAL_CONFIRM_1,
        WorkflowStage.MATERIAL_CONFIRM_2,
        WorkflowStage.MATERIAL_CONFIRM_3,
    )
    _add("material", "다음 단계 요청 필요", rows,
         sum(i.qty or 0 for i in rows))

    rows = _stage_items(WorkflowStage.MATERIAL_FINAL_CONFIRM)
    _add("material", "제품 출고 대기", rows,
         sum(i.qty or 0 for i in rows))

    reqs = _waiting_requests(WorkflowStage.PRODUCTION_REQUEST)
    _add("production", "생산 승인 대기", reqs,
         sum(r.request_qty or 0 for r in reqs))

    rows = _stage_items(WorkflowStage.PRODUCTION_APPROVAL)
    _add("production", "생산 완료 등록 필요", rows,
         sum(i.qty or 0 for i in rows))

    rows = _stage_items(WorkflowStage.PACKAGING_REQUEST)
    _add("production", "포장 완료 등록 필요", rows,
         sum(i.qty or 0 for i in rows))

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