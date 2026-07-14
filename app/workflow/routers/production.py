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
from app.workflow.models.workflow_remnant import WorkflowRemnant
from app.workflow.models.workflow_notification import WorkflowNotification
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

    all_remnants = get_remnants(db, department="production")
    work_defects = [r for r in all_remnants if r.reason == "WORK_DEFECT"]
    material_return_defects = [
        r for r in all_remnants if r.reason == "MATERIAL_RETURN_DEFECT"
    ]
    remnants = [
        r for r in all_remnants
        if r.reason not in ("WORK_DEFECT", "MATERIAL_RETURN_DEFECT")
    ]

    for row in all_remnants:
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
            "work_defects": work_defects,
            "work_defect_count": len(work_defects),
            "material_return_defects": material_return_defects,
            "material_return_defect_count": len(material_return_defects),
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


@router.post("/transfer-defects")
async def transfer_defects(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    raw_ids = form.getlist("remnant_ids")
    try:
        remnant_ids = [int(value) for value in raw_ids]
        if not remnant_ids:
            raise ValueError("자재팀으로 이관할 불량을 선택해 주세요.")
        rows = (
            db.query(WorkflowRemnant)
            .filter(WorkflowRemnant.id.in_(remnant_ids))
            .all()
        )
        if len(rows) != len(set(remnant_ids)):
            raise ValueError("선택한 불량 재고를 찾을 수 없습니다.")
        for row in rows:
            if (
                row.department != "production"
                or row.reason not in ("WORK_DEFECT", "MATERIAL_RETURN_DEFECT")
                or row.transfer_status == "PENDING"
            ):
                raise ValueError("이관할 수 없는 불량 재고가 포함되어 있습니다.")
            row.transfer_status = "PENDING"
            db.add(WorkflowNotification(
                workflow_no=row.workflow_no,
                department="material",
                title="생산 불량 자재 이관 승인 요청",
                message=(f"{row.item_code} {row.qty} EA · "
                         f"{row.source_warehouse or row.reason}"),
                notification_type="DEFECT_TRANSFER",
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        return _redirect(str(e))
    return _redirect()

@router.post("/complete-production-set")
async def complete_production_set(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    user = request.session.get("user", "SYSTEM")

    work_defects = {
        key[len("work_defect_"):]: int(value or 0)
        for key, value in form.items() if key.startswith("work_defect_")
    }
    return_defects = {
        key[len("material_return_defect_"):]: int(value or 0)
        for key, value in form.items() if key.startswith("material_return_defect_")
    }
    defect_breakdowns = {
        workflow_no: {
            "work": work_defects.get(workflow_no, 0),
            "return": return_defects.get(workflow_no, 0),
        }
        for workflow_no in set(work_defects) | set(return_defects)
    }
    defects = {key: value["work"] + value["return"] for key, value in defect_breakdowns.items()}

    service = WorkflowService(db)

    try:
        service.complete_production_set(
            target_code=form.get("target_code", ""),
            produced_qty=int(form.get("produced_qty", 0) or 0),
            lot=form.get("lot", ""),
            defects=defects,
            defect_breakdowns=defect_breakdowns,
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
    form = await request.form()
    user = request.session.get("user", "SYSTEM")
    work_defects = {key[len("work_defect_"):]: int(value or 0) for key, value in form.items() if key.startswith("work_defect_")}
    return_defects = {key[len("material_return_defect_"):]: int(value or 0) for key, value in form.items() if key.startswith("material_return_defect_")}
    defect_breakdowns = {workflow_no: {"work": work_defects.get(workflow_no, 0), "return": return_defects.get(workflow_no, 0)} for workflow_no in set(work_defects) | set(return_defects)}
    defects = {key: value["work"] + value["return"] for key, value in defect_breakdowns.items()}
    service = WorkflowService(db)

    try:
        service.complete_packaging_set(
            target_code=form.get("target_code", ""),
            produced_qty=int(form.get("produced_qty", 0) or 0),
            lot=form.get("lot", ""),
            defects=defects,
            defect_breakdowns=defect_breakdowns,
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
    work_defect_qty: int = Form(None),
    material_return_defect_qty: int = Form(None),
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
            work_defect_qty=work_defect_qty,
            material_return_defect_qty=material_return_defect_qty,
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
    work_defect_qty: int = Form(None),
    material_return_defect_qty: int = Form(None),
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
            work_defect_qty=work_defect_qty,
            material_return_defect_qty=material_return_defect_qty,
        )
    except Exception as e:
        return _redirect(str(e))

    return _redirect()