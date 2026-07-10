import os
from urllib.parse import quote
from fastapi import APIRouter, Depends, Form, File, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.workflow.utils import get_db
from app.workflow.services.workflow_service import WorkflowService
from app.workflow.services.inspection_service import (
    complete_incoming_inspection,
    complete_process_inspection,
    get_inspections,
)
from app.workflow.services.attachment_service import (
    save_inspection_attachment,
    delete_inspection_attachment,
)
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_inspection import WorkflowInspection
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_stage_name,
)

router = APIRouter(
    prefix="/workflow/quality",
    tags=["Workflow Quality"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


def _redirect(error: str = ""):
    url = "/workflow/quality"

    if error:
        url += f"?error={quote(error)}"

    return RedirectResponse(url, status_code=303)


@router.get("")
def quality_page(
    request: Request,
    db: Session = Depends(get_db),
):
    # 품질 입고 승인 대기 (2단계 요청)
    approval_rows = (
        db.query(WorkflowRequest, WorkflowItem)
        .join(
            WorkflowItem,
            WorkflowItem.workflow_no == WorkflowRequest.workflow_no,
        )
        .filter(
            WorkflowRequest.stage == int(WorkflowStage.QUALITY_REQUEST),
            WorkflowRequest.status == "WAITING",
        )
        .order_by(WorkflowRequest.id.asc())
        .all()
    )

    inspection_items = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage == int(
                WorkflowStage.QUALITY_APPROVAL
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowItem.id.asc())
        .all()
    )

    process_rows = (
        db.query(WorkflowRequest, WorkflowItem)
        .join(
            WorkflowItem,
            WorkflowItem.workflow_no == WorkflowRequest.workflow_no,
        )
        .filter(
            WorkflowRequest.stage == int(
                WorkflowStage.PROCESS_INSPECTION_REQUEST
            ),
            WorkflowRequest.status == "WAITING",
            WorkflowItem.current_stage == int(
                WorkflowStage.PROCESS_INSPECTION_REQUEST
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowRequest.id.asc())
        .all()
    )

    recent_inspections = get_inspections(db, limit=10)

    for row in recent_inspections:
        row.stage_name = get_stage_name(row.stage)

    return templates.TemplateResponse(
        request,
        "workflow/quality.html",
        {
            "approval_rows": approval_rows,
            "inspection_items": inspection_items,
            "process_rows": process_rows,
            "recent_inspections": recent_inspections,
            "approval_count": len(approval_rows),
            "approval_qty": sum(r.request_qty or 0 for r, _ in approval_rows),
            "inspection_count": len(inspection_items),
            "inspection_qty": sum(i.qty or 0 for i in inspection_items),
            "process_count": len(process_rows),
            "process_qty": sum(i.qty or 0 for _, i in process_rows),
            "completed_count": len(recent_inspections),
            "completed_qty": sum(i.good_qty or 0 for i in recent_inspections),
            "error": request.query_params.get("error", ""),
        },
    )


@router.post("/approve")
def approve(
    request: Request,
    request_id: int = Form(...),
    approved_qty: int = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.approve(
            request_id=request_id,
            approved_qty=approved_qty,
            approved_by=user,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/reject")
def reject(
    request: Request,
    request_id: int = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.reject(
            request_id=request_id,
            rejected_by=user,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/inspect")
def inspect(
    request: Request,
    workflow_no: str = Form(...),
    good_qty: int = Form(...),
    defect_qty: int = Form(0),
    remark: str = Form(""),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    try:
        complete_incoming_inspection(
            db,
            workflow_no=workflow_no,
            inspector=user,
            good_qty=good_qty,
            defect_qty=defect_qty,
            remark=remark,
            attachment=attachment,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/process-inspect")
def process_inspect(
    request: Request,
    workflow_no: str = Form(...),
    grade_a_qty: int = Form(0),
    grade_b_qty: int = Form(0),
    grade_f_qty: int = Form(0),
    remark: str = Form(""),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    try:
        complete_process_inspection(
            db,
            workflow_no=workflow_no,
            inspector=user,
            grade_a_qty=grade_a_qty,
            grade_b_qty=grade_b_qty,
            grade_f_qty=grade_f_qty,
            remark=remark,
            attachment=attachment,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.get("/inspection/{inspection_id}/attachment")
def download_attachment(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    inspection = (
        db.query(WorkflowInspection)
        .filter(WorkflowInspection.id == inspection_id)
        .first()
    )

    if (
        inspection is None
        or not inspection.attachment_path
        or not os.path.exists(inspection.attachment_path)
    ):
        return _redirect("첨부된 성적서를 찾을 수 없습니다.")

    return FileResponse(
        inspection.attachment_path,
        filename=inspection.attachment_name or "성적서",
    )


@router.post("/inspection/{inspection_id}/attachment/delete")
def delete_attachment(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    inspection = (
        db.query(WorkflowInspection)
        .filter(WorkflowInspection.id == inspection_id)
        .first()
    )

    if inspection is None:
        return _redirect("검사 이력을 찾을 수 없습니다.")

    delete_inspection_attachment(inspection.attachment_path)
    inspection.attachment_path = None
    inspection.attachment_name = None
    db.commit()

    return _redirect()


@router.post("/inspection/{inspection_id}/attachment")
def upload_attachment(
    inspection_id: int,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    최근 검사 이력에서 성적서를 삭제한 뒤 다시 첨부할 때 사용한다.
    """

    inspection = (
        db.query(WorkflowInspection)
        .filter(WorkflowInspection.id == inspection_id)
        .first()
    )

    if inspection is None:
        return _redirect("검사 이력을 찾을 수 없습니다.")

    if not attachment.filename:
        return _redirect("첨부할 파일을 선택해주세요.")

    # 기존 파일이 있다면 교체 전에 지운다.
    delete_inspection_attachment(inspection.attachment_path)

    path, name = save_inspection_attachment(inspection.id, attachment)
    inspection.attachment_path = path
    inspection.attachment_name = name
    db.commit()

    return _redirect()
