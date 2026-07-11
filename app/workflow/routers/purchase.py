from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.workflow.utils import get_db
from app.workflow.services.workflow_service import WorkflowService
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_stage_name,
)
from app.models.item_master import ItemMaster

router = APIRouter(
    prefix="/workflow/purchase",
    tags=["Workflow Purchase"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


def _redirect(error: str = ""):
    url = "/workflow/purchase"

    if error:
        url += f"?error={quote(error)}"

    return RedirectResponse(url, status_code=303)


def _parse_datetime_local(value: str):
    """datetime-local 입력값("YYYY-MM-DDTHH:MM") 파싱. 빈 값이면 None."""

    value = (value or "").strip()

    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(
            tzinfo=ZoneInfo("Asia/Seoul")
        )
    except ValueError:
        raise Exception("입고 일자 형식이 올바르지 않습니다.")

@router.get("")
def purchase_page(
    request: Request,
    db: Session = Depends(get_db),
):
    workflow_list = (
        db.query(WorkflowItem)
        .order_by(
            WorkflowItem.id.desc()
        )
        .all()
    )

    request_rows = (
        db.query(WorkflowRequest)
        .filter(
            WorkflowRequest.stage == int(WorkflowStage.QUALITY_REQUEST)
        )
        .order_by(WorkflowRequest.id.asc())
        .all()
    )

    inspection_requested_at = {}

    for row in request_rows:
        inspection_requested_at[row.workflow_no] = row.requested_at

    for item in workflow_list:
        item.purchase_display_code = (
            item.purchase_item_code
            or item.prev_item_code
            or item.item_code
        )
        item.purchase_display_name = (
            item.purchase_item_name
            or item.prev_item_name
            or item.item_name
        )
        item.purchase_display_lot = (
            item.purchase_lot
            or item.prev_lot
            or item.lot
        )
        item.current_stage_name = get_stage_name(
            item.current_stage
        )
        item.inspection_requested_at = inspection_requested_at.get(
            item.workflow_no
        )
        item.remnant_qty = (item.initial_qty or item.qty) - item.qty

    total_count = len(workflow_list)
    total_qty = sum(x.initial_qty or x.qty or 0 for x in workflow_list)

    progress_count = sum(
        1
        for x in workflow_list
        if x.status == "IN_PROGRESS"
    )
    progress_qty = sum(
        x.qty or 0
        for x in workflow_list
        if x.status == "IN_PROGRESS"
    )

    waiting_count = sum(
        1
        for x in workflow_list
        if x.current_stage == 2 and x.status == "IN_PROGRESS"
    )
    waiting_qty = sum(
        x.qty or 0
        for x in workflow_list
        if x.current_stage == 2 and x.status == "IN_PROGRESS"
    )

    completed_count = sum(
        1
        for x in workflow_list
        if x.status == "COMPLETED"
    )
    completed_qty = sum(
        x.qty or 0
        for x in workflow_list
        if x.status == "COMPLETED"
    )

    item_master_list = (
        db.query(ItemMaster)
        .order_by(ItemMaster.item_code)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "workflow/purchase.html",
        {
            "workflow_list": workflow_list,
            "total_count": total_count,
            "total_qty": total_qty,
            "progress_count": progress_count,
            "progress_qty": progress_qty,
            "waiting_count": waiting_count,
            "waiting_qty": waiting_qty,
            "completed_count": completed_count,
            "completed_qty": completed_qty,
            "item_master_list": item_master_list,
            "error": request.query_params.get("error", ""),
        },
    )

@router.post("/request")
def request_quality(
    request: Request,
    workflow_no: str = Form(...),
    qty: int = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):

    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.request_quality(
            workflow_no=workflow_no,
            qty=qty,
            requested_by=user,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()

@router.post("/create")
def create_workflow(
    item_code: str = Form(...),
    item_name: str = Form(...),
    lot: str = Form(""),
    rev: str = Form(""),
    qty: int = Form(...),
    service_type: str = Form(""),
    received_at: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db),

):

    user = request.session.get("user")
    service = WorkflowService(db)

    try:
        service.create_workflow(
            item_code=item_code,
            item_name=item_name,
            lot=lot,
            rev=rev,
            qty=qty,
            created_by=user,
            service_type=service_type,
            received_at=_parse_datetime_local(received_at),
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/update-item")
def update_item(
    request: Request,
    workflow_no: str = Form(...),
    item_code: str = Form(""),
    item_name: str = Form(""),
    lot: str = Form(""),
    received_at: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    구매팀 정보 수정 (품목코드/품명/LOT/입고 일자) - 품질 승인
    전(2단계 이하)까지만 수정할 수 있다. 이후 단계에서는 이 값들이
    검사/생산 기준 정보가 되므로 함부로 바꿀 수 없다. 품목코드/품명은
    등록 시 오타를 낸 경우를 되돌릴 수 있게 하기 위한 것으로, 이미
    잘못 입력된 코드를 고치는 용도이지 새 품목으로 바꾸는 용도가
    아니다.
    """

    item = (
        db.query(WorkflowItem)
        .filter(WorkflowItem.workflow_no == workflow_no)
        .first()
    )

    if item is None:
        return _redirect("Workflow를 찾을 수 없습니다.")

    if item.current_stage > int(WorkflowStage.QUALITY_REQUEST):
        return _redirect(
            "품질 승인 이후에는 구매 정보를 수정할 수 없습니다."
        )

    if not (item_code or "").strip():
        return _redirect("품목 코드는 필수 입력 항목입니다.")

    if not (item_name or "").strip():
        return _redirect("품명은 필수 입력 항목입니다.")

    try:
        parsed = _parse_datetime_local(received_at)
    except Exception as e:
        return _redirect(str(e))

    item.item_code = "".join(item_code.split())
    item.item_name = item_name.strip()
    item.lot = (lot or "").strip()
    item.purchase_item_code = item.item_code
    item.purchase_item_name = item.item_name
    item.purchase_lot = item.lot

    if parsed is not None:
        item.received_at = parsed

    item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

    db.commit()

    return _redirect()
