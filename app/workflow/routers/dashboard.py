import re
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.workflow.utils import get_db, department_name
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_stage import (
    STAGE_INFO,
    TOTAL_STAGE,
    get_stage_name,
)
from app.workflow.services.history_service import get_histories
from app.workflow.config import ACTION_NAMES

router = APIRouter(
    prefix="/workflow/dashboard",
    tags=["Workflow Dashboard"],
)

templates = Jinja2Templates(
    directory="app/templates"
)

@router.get("")
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
):
    items = (
        db.query(WorkflowItem)
        .order_by(WorkflowItem.id.desc())
        .all()
    )

    for item in items:
        item.current_stage_name = get_stage_name(item.current_stage)
        item.department_name = department_name(item.current_department)
        item.progress_percent = round(
            item.current_stage / TOTAL_STAGE * 100
        )

    total_count = len(items)
    total_qty = sum(x.initial_qty or x.qty or 0 for x in items)

    completed_count = sum(
        1 for x in items if x.status == "COMPLETED"
    )
    completed_qty = sum(
        x.qty or 0 for x in items if x.status == "COMPLETED"
    )

    progress_count = sum(
        1 for x in items if x.status == "IN_PROGRESS"
    )
    progress_qty = sum(
        x.qty or 0 for x in items if x.status == "IN_PROGRESS"
    )

    waiting_requests = (
        db.query(WorkflowRequest)
        .filter(WorkflowRequest.status == "WAITING")
        .all()
    )
    waiting_request_count = len(waiting_requests)
    waiting_request_qty = sum(r.request_qty or 0 for r in waiting_requests)
    size_shipped = {size: 0 for size in range(8, 14)}

    for item in items:
        if item.status != "COMPLETED":
            continue

        name = item.item_name or ""
        match = (
            re.search(r"size\s*(\d+)", name, re.IGNORECASE)
            or re.search(r"_(\d+)\s*$", name)
        )

        if not match:
            continue

        size = int(match.group(1))

        if size in size_shipped:
            size_shipped[size] += item.qty or 0

    size_labels = [f"{size}호" for size in size_shipped]
    size_values = list(size_shipped.values())
    department_counts = {"purchase": 0, "quality": 0, "material": 0, "production": 0}
    department_qtys = {"purchase": 0, "quality": 0, "material": 0, "production": 0}

    for item in items:
        if item.status == "IN_PROGRESS" and item.current_department in department_counts:
            department_counts[item.current_department] += 1
            department_qtys[item.current_department] += item.qty or 0

    department_summary = [
        {
            "code": code,
            "name": department_name(code),
            "count": count,
            "qty": department_qtys[code],
        }
        for code, count in department_counts.items()
    ]

    stages = [
        {
            "no": int(stage),
            "name": info["name"],
            "department": department_name(info["department"]),
        }
        for stage, info in STAGE_INFO.items()
    ]

    recent_histories = get_histories(db, limit=10)

    for row in recent_histories:
        row.stage_name = get_stage_name(row.stage)
        row.department_label = department_name(row.department)

    return templates.TemplateResponse(
        request,
        "workflow/dashboard.html",
        {
            "items": items,
            "stages": stages,
            "total_stage": TOTAL_STAGE,
            "total_count": total_count,
            "total_qty": total_qty,
            "progress_count": progress_count,
            "progress_qty": progress_qty,
            "completed_count": completed_count,
            "completed_qty": completed_qty,
            "waiting_request_count": waiting_request_count,
            "waiting_request_qty": waiting_request_qty,
            "department_summary": department_summary,
            "recent_histories": recent_histories,
            "size_labels": size_labels,
            "size_values": size_values,
            "action_names": ACTION_NAMES
        },
    )