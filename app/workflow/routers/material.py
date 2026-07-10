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
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_stage_name,
)

# 자재 확인 단계 -> 해당 확인이 참조해야 할 검사 종류. 품질 검사
# 결과를 확인하는 단계(입고검사/공정검사)에서만 성적서 링크를 보여준다.
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

        # 품질 검사 결과를 확인하는 단계라면, 첨부된 성적서가 있는
        # 가장 최근 검사 기록을 찾아 확인 모달에서 다운로드할 수
        # 있게 한다. 승인 판단에 필요한 수량 내역(양품/불량, A/B/F)도
        # 함께 만들어 모달에 보여준다.
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

        # 생산/포장 완료 확인 단계: 양품은 item.qty, 불량은 완료 시점에
        # 자재팀 불량 창고로 넘어온 잔존 기록(세트 구성품 포함)을 합산.
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
                if r.reason == "DEFECT"
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

        # CRADLE처럼 이미 반제품으로 구매되는 포장 구성품은 생산·
        # 공정검사가 필요 없어 자재 확인(5단계) 완료 후 곧바로 포장
        # 요청으로 넘어가야 하므로, 이 경우에만 표시 라벨을 다르게
        # 준다 (실제 라우팅은 request_next에서 처리).
        if (
            item.current_stage == int(WorkflowStage.MATERIAL_CONFIRM_1)
            and item.item_code in PREMADE_PACKAGING_CODES
        ):
            item.next_request_label = "포장 요청 (생산·공정검사 생략)"
        else:
            item.next_request_label = NEXT_REQUEST_LABELS[item.current_stage]

    # 출고 대기: 최종 확인(15)이 끝난 항목
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

    # 자재팀 창고는 불량과 양품을 분리해서 보여준다 - 불량 자재
    # 창고(품질/생산에서 넘어온 불량)와 양품 자재 창고(부분 승인/
    # 부분 요청/부분 출고로 남은 정상 재고).
    defect_remnants = [r for r in remnants if r.reason == "DEFECT"]
    good_remnants = [r for r in remnants if r.reason != "DEFECT"]

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


@router.post("/reject-stage")
def reject_stage(
    request: Request,
    workflow_no: str = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    자재 확인 단계 반려 - 직전 부서(품질/생산)가 재작업하도록 되돌린다.
    """

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
    """
    자재 확인 완료 단계에 맞는 다음 요청(생산/공정검사/포장)을 보낸다.
    """

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
            # CRADLE처럼 이미 반제품으로 구매되는 포장 구성품은 생산·
            # 공정검사 단계를 건너뛰고 곧바로 포장 요청으로 넘어간다.
            # 포장 요청은 별도 승인 절차가 없으므로(생산팀이 바로
            # 포장 진행) 의뢰 시점에 수량을 확정한다.
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
            # 생산 요청은 생산팀의 별도 승인 절차가 있다 - 여기서 수량을
            # 미리 확정하지 않고, 승인 시점(approve_request)에 확정해서
            # "승인 전까지는 기존 수량 유지, 승인 후 확정 수량으로 감소"
            # 가 지켜지도록 한다.
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

            # 포장 요청도 별도 승인 절차 없이 생산팀이 바로 포장을
            # 진행하므로 위와 동일하게 의뢰 시점에 확정한다.
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
