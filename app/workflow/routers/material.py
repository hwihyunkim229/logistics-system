from urllib.parse import quote
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.workflow.utils import get_db
from app.workflow.services.workflow_service import (
    WorkflowService,
    MATERIAL_CONFIRM_STAGES,
)
from app.workflow.services.remnant_service import (
    add_remnant,
    get_remnants,
)
from app.workflow.config import (
    REMNANT_REASON_NAMES,
    PREMADE_PACKAGING_CODES,
)
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_inspection import WorkflowInspection
from app.workflow.models.workflow_remnant import WorkflowRemnant
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_stage_name,
)

CONFIRM_INSPECTION_TYPE = {
    int(WorkflowStage.QUALITY_INSPECTION): "INCOMING",
    int(WorkflowStage.PROCESS_INSPECTION): "PROCESS",
}

router = APIRouter(
    prefix="/workflow/material",
    tags=["Workflow Material"],
)

templates = Jinja2Templates(
    directory="app/templates"
)

NEXT_REQUEST_LABELS = {
    int(WorkflowStage.MATERIAL_CONFIRM_1): "생산 요청",
    int(WorkflowStage.MATERIAL_CONFIRM_2): "공정 검사 의뢰",
    int(WorkflowStage.MATERIAL_CONFIRM_3): "포장 요청",
}

def _redirect(error: str = ""):
    url = "/workflow/material"

    if error:
        url += f"?error={quote(error)}"

    return RedirectResponse(url, status_code=303)

@router.get("")
def material_page(
    request: Request,
    db: Session = Depends(get_db),
):
    confirm_items = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage.in_(
                list(MATERIAL_CONFIRM_STAGES.keys())
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowItem.id.asc())
        .all()
    )

    for item in confirm_items:
        item.current_stage_name = get_stage_name(item.current_stage)
        item.confirm_label = get_stage_name(
            MATERIAL_CONFIRM_STAGES[item.current_stage]
        )

        item.inspection_attachment_id = None
        item.result_summary = ""
        inspection_type = CONFIRM_INSPECTION_TYPE.get(item.current_stage)

        if inspection_type:
            latest_inspection = (
                db.query(WorkflowInspection)
                .filter(
                    WorkflowInspection.workflow_no == item.workflow_no,
                    WorkflowInspection.inspection_type == inspection_type,
                )
                .order_by(WorkflowInspection.id.desc())
                .first()
            )

            if latest_inspection:
                if latest_inspection.attachment_path:
                    item.inspection_attachment_id = latest_inspection.id

                if inspection_type == "PROCESS":
                    item.result_summary = (
                        f"검사 {latest_inspection.request_qty} EA → "
                        f"A급 {latest_inspection.grade_a_qty} / "
                        f"B급 {latest_inspection.grade_b_qty} / "
                        f"F급(불량) {latest_inspection.grade_f_qty}"
                    )
                else:
                    item.result_summary = (
                        f"검사 {latest_inspection.request_qty} EA → "
                        f"양품 {latest_inspection.good_qty} / "
                        f"불량 {latest_inspection.defect_qty}"
                    )

        elif item.current_stage in (
            int(WorkflowStage.PRODUCTION_COMPLETE),
            int(WorkflowStage.PACKAGING_COMPLETE),
        ):
            merged_wf_nos = [
                row.workflow_no
                for row in db.query(WorkflowItem)
                .filter(WorkflowItem.merged_into == item.workflow_no)
                .all()
            ]

            defect_qty = sum(
                r.qty or 0
                for r in get_remnants(db, department="material")
                if r.reason in ("DEFECT", "WORK_DEFECT", "MATERIAL_RETURN_DEFECT")
                and r.stage == item.current_stage
                and r.workflow_no in ([item.workflow_no] + merged_wf_nos)
            )

            action_label = (
                "생산"
                if item.current_stage == int(
                    WorkflowStage.PRODUCTION_COMPLETE
                )
                else "포장"
            )
            item.result_summary = (
                f"{action_label} 결과 → 양품 {item.qty} / 불량 {defect_qty}"
            )

    request_items = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage.in_(
                list(NEXT_REQUEST_LABELS.keys())
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowItem.id.asc())
        .all()
    )

    for item in request_items:
        item.current_stage_name = get_stage_name(item.current_stage)

        if (
            item.current_stage == int(WorkflowStage.MATERIAL_CONFIRM_1)
            and item.item_code in PREMADE_PACKAGING_CODES
        ):
            item.next_request_label = "포장 요청 (생산·공정검사 생략)"
        else:
            item.next_request_label = NEXT_REQUEST_LABELS[item.current_stage]

    ship_items = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage == int(
                WorkflowStage.MATERIAL_FINAL_CONFIRM
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowItem.id.asc())
        .all()
    )

    shipped_items = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage == int(
                WorkflowStage.SERVICE_SHIPMENT
            ),
            WorkflowItem.status != "MERGED",
        )
        .all()
    )

    remnants = get_remnants(db, department="material")

    for row in remnants:
        row.stage_name = get_stage_name(row.stage)
        row.reason_label = REMNANT_REASON_NAMES.get(row.reason, row.reason)

    defect_remnants = [r for r in remnants if r.reason == "DEFECT"]
    defect_remnants += [
        r for r in remnants
        if r.reason in ("WORK_DEFECT", "MATERIAL_RETURN_DEFECT")
    ]
    good_remnants = [r for r in remnants if r.reason != "DEFECT"]
    good_remnants = [
        r for r in good_remnants
        if r.reason not in ("WORK_DEFECT", "MATERIAL_RETURN_DEFECT")
    ]
    pending_defect_transfers = (
        db.query(WorkflowRemnant)
        .filter(
            WorkflowRemnant.department == "production",
            WorkflowRemnant.transfer_status == "PENDING",
            WorkflowRemnant.reason.in_(("WORK_DEFECT", "MATERIAL_RETURN_DEFECT")),
        )
        .order_by(WorkflowRemnant.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "workflow/material.html",
        {
            "confirm_items": confirm_items,
            "request_items": request_items,
            "ship_items": ship_items,
            "confirm_count": len(confirm_items),
            "confirm_qty": sum(i.qty or 0 for i in confirm_items),
            "request_count": len(request_items),
            "request_qty": sum(i.qty or 0 for i in request_items),
            "ship_count": len(ship_items),
            "ship_qty": sum(i.qty or 0 for i in ship_items),
            "shipped_count": len(shipped_items),
            "shipped_qty": sum(i.qty or 0 for i in shipped_items),
            "defect_remnants": defect_remnants,
            "defect_remnant_count": len(defect_remnants),
            "pending_defect_transfers": pending_defect_transfers,
            "good_remnants": good_remnants,
            "good_remnant_count": len(good_remnants),
            "error": request.query_params.get("error", ""),
        },
    )

@router.post("/confirm")
def confirm(
    request: Request,
    workflow_no: str = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.material_confirm(
            workflow_no=workflow_no,
            confirmed_by=user,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/approve-defect-transfer")
def approve_defect_transfer(
    request: Request,
    remnant_id: int = Form(...),
    db: Session = Depends(get_db),
):
    row = db.query(WorkflowRemnant).filter(WorkflowRemnant.id == remnant_id).first()
    if (
        row is None
        or row.department != "production"
        or row.transfer_status != "PENDING"
    ):
        return _redirect("승인 대기 중인 생산 불량 이관 요청을 찾을 수 없습니다.")
    row.department = "material"
    row.transfer_status = "APPROVED"
    db.commit()
    return _redirect()


@router.post("/reject-defect-transfer")
def reject_defect_transfer(
    request: Request,
    remnant_id: int = Form(...),
    db: Session = Depends(get_db),
):
    row = db.query(WorkflowRemnant).filter(WorkflowRemnant.id == remnant_id).first()
    if (
        row is None
        or row.department != "production"
        or row.transfer_status != "PENDING"
    ):
        return _redirect("승인 대기 중인 생산 불량 이관 요청을 찾을 수 없습니다.")
    row.transfer_status = "AVAILABLE"
    db.commit()
    return _redirect()

@router.post("/reject-stage")
def reject_stage(
    request: Request,
    workflow_no: str = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.material_reject(
            workflow_no=workflow_no,
            rejected_by=user,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()

@router.post("/request-next")
def request_next(
    request: Request,
    workflow_no: str = Form(...),
    qty: int = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    item = (
        db.query(WorkflowItem)
        .filter(WorkflowItem.workflow_no == workflow_no)
        .first()
    )

    if item is None:
        return _redirect("Workflow를 찾을 수 없습니다.")

    if qty < 1 or qty > item.qty:
        return _redirect("요청 수량이 올바르지 않습니다.")

    service = WorkflowService(db)

    try:
        if (
            item.current_stage == int(WorkflowStage.MATERIAL_CONFIRM_1)
            and item.item_code in PREMADE_PACKAGING_CODES
        ):
            
            leftover = item.qty - qty

            service.request_packaging_direct(
                workflow_no=workflow_no,
                qty=qty,
                requested_by=user,
                remark=remark,
            )

            if leftover > 0:
                item.qty = qty
                add_remnant(
                    db,
                    workflow_no=workflow_no,
                    stage=int(WorkflowStage.PACKAGING_REQUEST),
                    department="material",
                    item_code=item.item_code,
                    item_name=item.item_name,
                    lot=item.lot,
                    qty=leftover,
                    reason="PARTIAL_REQUEST",
                )
                db.commit()

        elif item.current_stage == int(WorkflowStage.MATERIAL_CONFIRM_1):

            service.request_production(
                workflow_no=workflow_no,
                qty=qty,
                requested_by=user,
                remark=remark,
            )

        elif item.current_stage == int(WorkflowStage.MATERIAL_CONFIRM_2):
            leftover = item.qty - qty

            service.request_process_inspection(
                workflow_no=workflow_no,
                qty=qty,
                requested_by=user,
                remark=remark,
            )

            if leftover > 0:
                item.qty = qty
                add_remnant(
                    db,
                    workflow_no=workflow_no,
                    stage=int(WorkflowStage.PROCESS_INSPECTION_REQUEST),
                    department="material",
                    item_code=item.item_code,
                    item_name=item.item_name,
                    lot=item.lot,
                    qty=leftover,
                    reason="PARTIAL_REQUEST",
                )
                db.commit()

        elif item.current_stage == int(WorkflowStage.MATERIAL_CONFIRM_3):
            leftover = item.qty - qty

            service.request_packaging(
                workflow_no=workflow_no,
                qty=qty,
                requested_by=user,
                remark=remark,
            )

            if leftover > 0:
                item.qty = qty
                add_remnant(
                    db,
                    workflow_no=workflow_no,
                    stage=int(WorkflowStage.PACKAGING_REQUEST),
                    department="material",
                    item_code=item.item_code,
                    item_name=item.item_name,
                    lot=item.lot,
                    qty=leftover,
                    reason="PARTIAL_REQUEST",
                )
                db.commit()

        else:
            return _redirect(
                f"요청을 보낼 수 없는 단계입니다. "
                f"(현재: {get_stage_name(item.current_stage)})"
            )

    except Exception as e:
        return _redirect(str(e))

    return _redirect()

@router.post("/ship")
def ship(
    request: Request,
    workflow_no: str = Form(...),
    qty: int = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.ship_service(
            workflow_no=workflow_no,
            shipped_by=user,
            ship_qty=qty,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()