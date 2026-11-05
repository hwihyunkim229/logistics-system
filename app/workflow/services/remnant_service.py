from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.workflow.models.workflow_remnant import WorkflowRemnant
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_stage import WorkflowStage
from app.workflow.services.history_service import add_history
from app.workflow.config import PREMADE_PACKAGING_CODES

def add_remnant(
    db: Session,
    workflow_no: str,
    stage: int,
    department: str,
    item_code: str,
    item_name: str,
    lot: str,
    qty: int,
    reason: str,
    source_warehouse: str = "",
    transfer_status: str = "AVAILABLE",
):
    if qty <= 0:
        return None

    remnant = WorkflowRemnant(
        workflow_no=workflow_no,
        stage=stage,
        department=department,
        item_code=item_code,
        item_name=item_name,
        lot=lot,
        qty=qty,
        reason=reason,
        source_warehouse=source_warehouse,
        transfer_status=transfer_status,
    )

    db.add(remnant)

    return remnant

def clear_remnants(
    db: Session,
    workflow_no: str,
    stage: int,
):
    rows = (
        db.query(WorkflowRemnant)
        .filter(
            WorkflowRemnant.workflow_no == workflow_no,
            WorkflowRemnant.stage == stage,
        )
        .all()
    )

    for row in rows:
        db.delete(row)

    return len(rows)

def remnant_qty_by_item(
    db: Session,
    department: str,
    reason: str,
    item_code: str,
):
    rows = (
        db.query(WorkflowRemnant)
        .filter(
            WorkflowRemnant.department == department,
            WorkflowRemnant.reason == reason,
            WorkflowRemnant.item_code == item_code,
        )
        .all()
    )

    return sum(row.qty or 0 for row in rows)

def consume_remnant_pool(
    db: Session,
    department: str,
    reason: str,
    item_code: str,
    qty: int,
):
    if qty <= 0:
        return 0

    rows = (
        db.query(WorkflowRemnant)
        .filter(
            WorkflowRemnant.department == department,
            WorkflowRemnant.reason == reason,
            WorkflowRemnant.item_code == item_code,
        )
        .order_by(WorkflowRemnant.id.asc())
        .all()
    )

    remaining = qty
    consumed = 0

    for row in rows:
        if remaining <= 0:
            break

        take = min(row.qty or 0, remaining)
        row.qty = (row.qty or 0) - take
        remaining -= take
        consumed += take

        if row.qty <= 0:
            db.delete(row)

    return consumed

def pop_remnant_qty(
    db: Session,
    workflow_no: str,
    stage: int,
    department: str,
    reason: str,
):
    rows = (
        db.query(WorkflowRemnant)
        .filter(
            WorkflowRemnant.workflow_no == workflow_no,
            WorkflowRemnant.stage == stage,
            WorkflowRemnant.department == department,
            WorkflowRemnant.reason == reason,
        )
        .all()
    )

    remaining = 0

    for row in rows:
        remaining += row.qty or 0
        db.delete(row)

    return remaining

def get_remnants(
    db: Session,
    department: str = "",
    workflow_no: str = "",
    limit: int = 200,
):
    query = db.query(WorkflowRemnant)

    if department:
        query = query.filter(
            WorkflowRemnant.department == department
        )

    if workflow_no:
        query = query.filter(
            WorkflowRemnant.workflow_no == workflow_no
        )

    return (
        query
        .order_by(WorkflowRemnant.id.desc())
        .limit(limit)
        .all()
    )

def restock_remnant(
    db: Session,
    remnant_id: int,
    restocked_by: str,
):
    from app.workflow.services.workflow_service import WorkflowService

    remnant = (
        db.query(WorkflowRemnant)
        .filter(WorkflowRemnant.id == remnant_id)
        .first()
    )

    if remnant is None:
        raise Exception("잔존 자재 기록을 찾을 수 없습니다.")

    if remnant.qty <= 0:
        raise Exception("재입고할 수량이 없습니다.")

    origin_item = (
        db.query(WorkflowItem)
        .filter(WorkflowItem.workflow_no == remnant.workflow_no)
        .first()
    )

    item_code = remnant.item_code
    item_name = remnant.item_name
    lot = remnant.lot or f"RESTOCK-{remnant.id}"
    qty = remnant.qty
    service_type = origin_item.service_type if origin_item else ""

    service = WorkflowService(db)

    if remnant.reason in ("PARTIAL_SHIP", "PARTIAL_REQUEST"):
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        today = now.strftime("%Y%m%d")
        if remnant.reason == "PARTIAL_SHIP":
            target_stage = int(WorkflowStage.MATERIAL_FINAL_CONFIRM)
        elif remnant.stage == int(WorkflowStage.PROCESS_INSPECTION_REQUEST):
            target_stage = int(WorkflowStage.MATERIAL_CONFIRM_2)
        elif item_code in PREMADE_PACKAGING_CODES:
            target_stage = int(WorkflowStage.MATERIAL_CONFIRM_1)
        else:
            target_stage = int(WorkflowStage.MATERIAL_CONFIRM_3)
        item = WorkflowItem(
            workflow_no="TEMP",
            item_code=item_code,
            item_name=item_name,
            purchase_item_code=(origin_item.purchase_item_code if origin_item else item_code),
            purchase_item_name=(origin_item.purchase_item_name if origin_item else item_name),
            purchase_lot=(origin_item.purchase_lot if origin_item else lot),
            lot=lot,
            rev=origin_item.rev if origin_item else "",
            qty=qty,
            initial_qty=qty,
            process_qty=qty,
            received_at=origin_item.received_at if origin_item else now,
            prev_item_code=origin_item.prev_item_code if origin_item else None,
            prev_item_name=origin_item.prev_item_name if origin_item else None,
            prev_lot=origin_item.prev_lot if origin_item else None,
            current_stage=target_stage,
            current_department="material",
            status="IN_PROGRESS",
            created_by=restocked_by,
            service_type=service_type,
        )
        db.add(item)
        db.flush()
        seq = service._next_workflow_seq(today)
        item.workflow_no = f"WF-{today}-{seq:06d}"
        add_history(
            db,
            workflow_no=item.workflow_no,
            stage=target_stage,
            action="RESTORE",
            user_name=restocked_by,
            department="material",
            before_qty=0,
            after_qty=qty,
            remark=(
                f"{remnant.workflow_no} "
                f"{'부분 출고' if remnant.reason == 'PARTIAL_SHIP' else '부분 요청'} "
                f"잔량 복구 "
                f"({qty} EA)"
            ),
        )
        db.delete(remnant)
        db.commit()
        db.refresh(item)
        return item

    db.delete(remnant)
    db.commit()

    return service.create_workflow(
        item_code=item_code,
        item_name=item_name,
        lot=lot,
        rev="",
        qty=qty,
        created_by=restocked_by,
        service_type=service_type,
    )

def remnant_qty_by_workflow(
    db: Session,
    department: str,
):
    rows = (
        db.query(WorkflowRemnant)
        .filter(WorkflowRemnant.department == department)
        .all()
    )

    totals = {}

    for row in rows:
        totals[row.workflow_no] = (
            totals.get(row.workflow_no, 0) + (row.qty or 0)
        )

    return totals
