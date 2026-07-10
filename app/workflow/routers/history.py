from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.workflow.utils import (
    get_db,
    department_name,
    action_name,
)
from app.workflow.services.history_service import get_histories
from app.workflow.models.workflow_stage import get_stage_name

router = APIRouter(
    prefix="/workflow/history",
    tags=["Workflow History"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


@router.get("")
def history_page(
    request: Request,
    workflow_no: str = "",
    department: str = "",
    db: Session = Depends(get_db),
):
    histories = get_histories(
        db,
        workflow_no=workflow_no.strip(),
        department=department.strip(),
        limit=300,
    )

    for row in histories:
        row.stage_name = get_stage_name(row.stage)
        row.department_label = department_name(row.department)
        row.action_label = action_name(row.action)

    return templates.TemplateResponse(
        request,
        "workflow/history.html",
        {
            "histories": histories,
            "workflow_no": workflow_no,
            "department": department,
            "total_count": len(histories),
        },
    )
