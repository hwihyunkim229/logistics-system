from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.workflow.utils import get_db
from app.workflow.services.workflow_service import WorkflowService
from app.workflow.services.remnant_service import (
    get_remnants,
    remnant_qty_by_item,
)
import json

from app.workflow.config import (
    REMNANT_REASON_NAMES,
    PRODUCTION_TRANSFORM,
    PACKAGING_TRANSFORM,
    PRODUCTION_COMPONENTS,
    PACKAGING_COMPONENTS,
)
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_stage_name,
)

router = APIRouter(
    prefix="/workflow/production",
    tags=["Workflow Production"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


def _redirect(error: str = ""):
    url = "/workflow/production"

    if error:
        url += f"?error={quote(error)}"

    return RedirectResponse(url, status_code=303)


@router.get("")
def production_page(
    request: Request,
    db: Session = Depends(get_db),
):
    approval_rows = (
        db.query(WorkflowRequest, WorkflowItem)
        .join(
            WorkflowItem,
            WorkflowItem.workflow_no == WorkflowRequest.workflow_no,
        )
        .filter(
            WorkflowRequest.stage == int(
                WorkflowStage.PRODUCTION_REQUEST
            ),
            WorkflowRequest.status == "WAITING",
        )
        .order_by(WorkflowRequest.id.asc())
        .all()
    )

    production_items = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage == int(
                WorkflowStage.PRODUCTION_APPROVAL
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowItem.id.asc())
        .all()
    )

    packaging_rows = (
        db.query(WorkflowRequest, WorkflowItem)
        .join(
            WorkflowItem,
            WorkflowItem.workflow_no == WorkflowRequest.workflow_no,
        )
        .filter(
            WorkflowRequest.stage == int(
                WorkflowStage.PACKAGING_REQUEST
            ),
            WorkflowRequest.status == "WAITING",
            WorkflowItem.current_stage == int(
                WorkflowStage.PACKAGING_REQUEST
            ),
            WorkflowItem.status == "IN_PROGRESS",
        )
        .order_by(WorkflowRequest.id.asc())
        .all()
    )

    completed_qty = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.current_stage >= int(
                WorkflowStage.PRODUCTION_COMPLETE
            ),
            WorkflowItem.status != "MERGED",
        )
        .all()
    )

    def _build_sets(items, components_map, transform_map):
        """구성품 목록을 세트(결과물) 단위로 묶는다.

        각 세트는 필요한 구성품 코드 전체와, 실제 도착한 workflow를
        짝지어 보여준다 - 전부 도착해야 완료 버튼이 활성화된다.
        """

        by_target = {}

        for item in items:
            nxt = transform_map.get(item.item_code)

            if not nxt:
                continue

            target_code, target_name = nxt
            group = by_target.setdefault(target_code, {
                "target_code": target_code,
                "target_name": target_name,
                "components": {},
            })
            group["components"].setdefault(item.item_code, []).append(item)

        sets = []

        for target_code, group in by_target.items():
            required = components_map.get(target_code, [])
            rows = []
            extras = []
            ready = True
            max_producible = None

            for code in required:
                matched = group["components"].get(code, [])

                leftover_qty = remnant_qty_by_item(
                    db,
                    department="production",
                    reason="SET_LEFTOVER",
                    item_code=code,
                )

                if not matched:
                    ready = False
                    rows.append({
                        "item_code": code,
                        "present": False,
                        "workflow_no": "",
                        "item_name": "",
                        "lot": "",
                        "qty": 0,
                        "leftover_qty": leftover_qty,
                    })
                    continue

                # 같은 코드의 workflow가 여러 건이면 먼저 도착한 건만
                # 이번 세트에 투입되고, 나머지는 완료 시 잔존 풀로
                # 보관된다 (workflow_service._complete_set 참고).
                for dup in matched[1:]:
                    extras.append({
                        "item_code": dup.item_code,
                        "workflow_no": dup.workflow_no,
                        "lot": dup.lot or "",
                        "qty": dup.qty,
                    })

                comp = matched[0]
                effective_qty = comp.qty + leftover_qty
                rows.append({
                    "item_code": comp.item_code,
                    "present": True,
                    "workflow_no": comp.workflow_no,
                    "item_name": comp.item_name,
                    "lot": comp.lot or "",
                    "qty": comp.qty,
                    "leftover_qty": leftover_qty,
                })

                if max_producible is None or effective_qty < max_producible:
                    max_producible = effective_qty

            sets.append({
                "target_code": group["target_code"],
                "target_name": group["target_name"],
                "rows": rows,
                "extras": extras,
                "ready": ready,
                "max_producible": max_producible or 0 if ready else 0,
                "components_json": json.dumps([
                    r for r in rows if r["present"]
                ], ensure_ascii=False),
            })

        return sets

    production_sets = _build_sets(
        production_items, PRODUCTION_COMPONENTS, PRODUCTION_TRANSFORM
    )

    packaging_items_only = [item for _, item in packaging_rows]
    packaging_sets = _build_sets(
        packaging_items_only, PACKAGING_COMPONENTS, PACKAGING_TRANSFORM
    )

    plain_production_items = [
        item for item in production_items
        if not PRODUCTION_TRANSFORM.get(item.item_code)
    ]

    plain_packaging_rows = [
        (req, item) for req, item in packaging_rows
        if not PACKAGING_TRANSFORM.get(item.item_code)
    ]

    remnants = get_remnants(db, department="production")

    for row in remnants:
        row.stage_name = get_stage_name(row.stage)
        row.reason_label = REMNANT_REASON_NAMES.get(row.reason, row.reason)

    return templates.TemplateResponse(
        request,
        "workflow/production.html",
        {
            "approval_rows": approval_rows,
            "production_sets": production_sets,
            "packaging_sets": packaging_sets,
            "plain_production_items": plain_production_items,
            "plain_packaging_rows": plain_packaging_rows,
            "approval_count": len(approval_rows),
            "approval_qty": sum(r.request_qty or 0 for r, _ in approval_rows),
            "production_count": len(production_items),
            "production_qty": sum(i.qty or 0 for i in production_items),
            "packaging_count": len(packaging_rows),
            "packaging_qty": sum(i.qty or 0 for i in packaging_items_only),
            "completed_count": len(completed_qty),
            "completed_qty": sum(i.qty or 0 for i in completed_qty),
            "remnants": remnants,
            "remnant_count": len(remnants),
            "remnant_title": "현 재고 현황",
            "remnant_show_restock": False,
            "remnant_show_production_use": True,
            "error": request.query_params.get("error", ""),
        },
    )


@router.post("/use-remnant")
def use_remnant(
    request: Request,
    remnant_id: int = Form(...),
    qty: int = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")
    service = WorkflowService(db)

    try:
        service.use_production_remnant(
            remnant_id=remnant_id,
            qty=qty,
            used_by=user,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/complete-production-set")
async def complete_production_set(
    request: Request,
    db: Session = Depends(get_db),
):
    """세트 생산 완료 - 구성품별 불량 수량은 defect_<workflow_no>
    필드로 전달된다."""

    form = await request.form()
    user = request.session.get("user", "SYSTEM")

    defects = {
        key[len("defect_"):]: int(value or 0)
        for key, value in form.items()
        if key.startswith("defect_")
    }

    service = WorkflowService(db)

    try:
        service.complete_production_set(
            target_code=form.get("target_code", ""),
            produced_qty=int(form.get("produced_qty", 0) or 0),
            lot=form.get("lot", ""),
            defects=defects,
            completed_by=user,
            remark=form.get("remark", ""),
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/complete-packaging-set")
async def complete_packaging_set(
    request: Request,
    db: Session = Depends(get_db),
):
    """제품 포장 적용 완료 - 구성품별 불량 수량은 defect_<workflow_no>
    필드로 전달된다."""

    form = await request.form()
    user = request.session.get("user", "SYSTEM")

    defects = {
        key[len("defect_"):]: int(value or 0)
        for key, value in form.items()
        if key.startswith("defect_")
    }

    service = WorkflowService(db)

    try:
        service.complete_packaging_set(
            target_code=form.get("target_code", ""),
            produced_qty=int(form.get("produced_qty", 0) or 0),
            lot=form.get("lot", ""),
            defects=defects,
            completed_by=user,
            remark=form.get("remark", ""),
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


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


@router.post("/complete-production")
def complete_production(
    request: Request,
    workflow_no: str = Form(...),
    good_qty: int = Form(...),
    defect_qty: int = Form(0),
    lot: str = Form(""),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.complete_production(
            workflow_no=workflow_no,
            completed_by=user,
            good_qty=good_qty,
            defect_qty=defect_qty,
            lot=lot,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()


@router.post("/complete-packaging")
def complete_packaging(
    request: Request,
    workflow_no: str = Form(...),
    good_qty: int = Form(...),
    defect_qty: int = Form(0),
    lot: str = Form(""),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    service = WorkflowService(db)

    try:
        service.complete_packaging(
            workflow_no=workflow_no,
            completed_by=user,
            good_qty=good_qty,
            defect_qty=defect_qty,
            lot=lot,
            remark=remark,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()
