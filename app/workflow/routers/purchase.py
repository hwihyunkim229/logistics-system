from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from fastapi.responses import StreamingResponse
from zoneinfo import ZoneInfo
from urllib.parse import quote
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
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
from app.workflow.config import ITEM_LIST

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

def _parse_excel_datetime(value):
    if pd.isna(value) or str(value).strip() == "":
        raise ValueError("입고 일자는 필수입니다.")
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("입고 일자 형식이 올바르지 않습니다.")
    parsed = parsed.to_pydatetime()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return parsed.astimezone(ZoneInfo("Asia/Seoul"))

def _excel_value(row, column):
    value = row[column]
    return "" if pd.isna(value) else str(value).strip()

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
    inspection_requested_qty = {}

    for row in request_rows:
        inspection_requested_at[row.workflow_no] = row.requested_at
        inspection_requested_qty[row.workflow_no] = (
            inspection_requested_qty.get(row.workflow_no, 0)
            + (row.request_qty or 0)
        )

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
        item.purchase_received_at = item.received_at or item.created_at
        item.purchase_remain_qty = max(
            (item.initial_qty or item.qty or 0)
            - inspection_requested_qty.get(item.workflow_no, 0),
            0,
        )

    total_count = len(workflow_list)
    total_qty = sum(x.initial_qty or x.qty or 0 for x in workflow_list)

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

    item_master_list = ITEM_LIST

    return templates.TemplateResponse(
        request,
        "workflow/purchase.html",
        {
            "workflow_list": workflow_list,
            "total_count": total_count,
            "total_qty": total_qty,
            "waiting_count": waiting_count,
            "waiting_qty": waiting_qty,
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
        item = (
            db.query(WorkflowItem)
            .filter(WorkflowItem.workflow_no == workflow_no)
            .first()
        )
        if item is None:
            raise ValueError("Workflow를 찾을 수 없습니다.")
        if item.current_stage != int(WorkflowStage.PURCHASE_RECEIVED):
            raise ValueError("구매 입고 단계의 항목만 수입 검사를 의뢰할 수 있습니다.")
        if qty < 1 or qty > (item.qty or 0):
            raise ValueError("검사 의뢰 수량은 현재 입고 수량 이하여야 합니다.")
        service.request_quality(
            workflow_no=workflow_no,
            qty=qty,
            requested_by=user,
            remark=remark,
        )
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return _redirect(str(e))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"ok": True})
    return _redirect()

@router.post("/upload-excel")
async def upload_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith((".xlsx", ".xls")):
        return _redirect("엑셀 파일(.xlsx 또는 .xls)만 업로드할 수 있습니다.")

    try:
        frame = pd.read_excel(BytesIO(await file.read()))
    except Exception:
        return _redirect("엑셀 파일을 읽을 수 없습니다.")

    required = ["Product", "품목코드", "품명", "LOT", "입고 수량", "입고 일자"]
    headers = {str(column).strip(): column for column in frame.columns}
    missing = [column for column in required if column not in headers]
    if missing:
        return _redirect("필수 열이 없습니다: " + ", ".join(missing))

    user = request.session.get("user", "SYSTEM")
    service = WorkflowService(db)
    created = 0
    try:
        for index, row in frame.iterrows():
            values = [_excel_value(row, headers[column]) for column in required]
            if not any(values):
                continue
            product, item_code, item_name, lot, qty_text, _ = values
            if not all((product, item_code, item_name, lot, qty_text)):
                raise ValueError(f"{index + 2}행의 필수 값을 확인해 주세요.")
            try:
                qty = int(float(qty_text.replace(",", "")))
            except ValueError:
                raise ValueError(f"{index + 2}행의 수량이 올바르지 않습니다.")
            if qty < 1:
                raise ValueError(f"{index + 2}행의 수량은 1 이상이어야 합니다.")
            service.create_workflow(
                item_code=item_code,
                item_name=item_name,
                lot=lot,
                rev="",
                qty=qty,
                created_by=user,
                service_type=product,
                received_at=_parse_excel_datetime(row[headers["입고 일자"]]),
            )
            created += 1
        if not created:
            raise ValueError("등록할 데이터가 없습니다.")
    except Exception as e:
        db.rollback()
        return _redirect(str(e))

    return _redirect(f"엑셀 업로드가 완료되었습니다. {created}건의 Workflow가 등록되었습니다.")

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

@router.get("/template")
def download_template():

    wb = Workbook()
    ws = wb.active
    ws.title = "Workflow Upload"

    ws.append([
        "Product",
        "품목코드",
        "품명",
        "LOT",
        "입고 수량",
        "입고 일자",
    ])

    ws.append([
        "CART-Platform",
        "SL-P-PD-00110",
        "CART PLATFORM IEM_size 8",
        "F260701",
        100,
        "2026-07-14 09:00",
    ])

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 35
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 22

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="workflow_upload_template.xlsx"'
        },
    )