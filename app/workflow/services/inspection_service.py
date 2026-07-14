from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_inspection import WorkflowInspection
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_next_stage,
    get_stage_name,
)
from app.workflow.services.history_service import add_history
from app.workflow.services.notification_service import add_notification
from app.workflow.services.remnant_service import add_remnant
from app.workflow.services.attachment_service import save_inspection_attachment

def _get_item(db: Session, workflow_no: str):
    item = (
        db.query(WorkflowItem)
        .filter(WorkflowItem.workflow_no == workflow_no)
        .first()
    )

    if item is None:
        raise Exception("Workflow를 찾을 수 없습니다.")

    return item

def complete_incoming_inspection(
    db: Session,
    workflow_no: str,
    inspector: str,
    good_qty: int,
    defect_qty: int,
    remark: str = "",
    attachment=None,
):
    item = _get_item(db, workflow_no)

    if item.current_stage != int(WorkflowStage.QUALITY_APPROVAL):
        raise Exception(
            f"수입 검사를 진행할 수 없는 단계입니다. "
            f"(현재: {get_stage_name(item.current_stage)})"
        )

    before_qty = item.qty

    inspection = WorkflowInspection(
        workflow_no=workflow_no,
        stage=int(WorkflowStage.QUALITY_INSPECTION),
        inspection_type="INCOMING",
        inspector=inspector,
        request_qty=before_qty,
        good_qty=good_qty,
        defect_qty=defect_qty,
        result="PASS" if defect_qty == 0 else "PARTIAL",
        remark=remark,
        is_completed=True,
    )

    db.add(inspection)

    if attachment is not None and getattr(attachment, "filename", ""):
        db.flush()
        path, name = save_inspection_attachment(inspection.id, attachment)
        inspection.attachment_path = path
        inspection.attachment_name = name

    item.current_stage = int(WorkflowStage.QUALITY_INSPECTION)
    item.current_department = "material"
    item.qty = good_qty
    item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

    add_remnant(
        db,
        workflow_no=workflow_no,
        stage=int(WorkflowStage.QUALITY_INSPECTION),
        department="material",
        item_code=item.item_code,
        item_name=item.item_name,
        lot=item.lot,
        qty=defect_qty,
        reason="DEFECT",
    )

    add_history(
        db,
        workflow_no=workflow_no,
        stage=int(WorkflowStage.QUALITY_INSPECTION),
        action="INSPECT",
        user_name=inspector,
        department="quality",
        before_qty=before_qty,
        after_qty=good_qty,
        remark=remark or f"수입 검사 완료 (양품 {good_qty} / 불량 {defect_qty})",
    )

    add_notification(
        db,
        workflow_no=workflow_no,
        department="material",
        title="수입 검사 완료",
        message=(
            f"{workflow_no} 수입 검사가 완료되었습니다. "
            f"(양품 {good_qty} / 불량 {defect_qty}) 자재 확인이 필요합니다."
        ),
        notification_type="INSPECTION",
    )

    db.commit()
    db.refresh(inspection)

    return inspection

def complete_process_inspection(
    db: Session,
    workflow_no: str,
    inspector: str,
    grade_a_qty: int,
    grade_b_qty: int,
    grade_f_qty: int,
    remark: str = "",
    attachment=None,
):
    item = _get_item(db, workflow_no)

    if item.current_stage != int(WorkflowStage.PROCESS_INSPECTION_REQUEST):
        raise Exception(
            f"공정 검사를 진행할 수 없는 단계입니다. "
            f"(현재: {get_stage_name(item.current_stage)})"
        )

    before_qty = item.qty
    good_qty = grade_a_qty + grade_b_qty
    defect_qty = grade_f_qty

    inspection = WorkflowInspection(
        workflow_no=workflow_no,
        stage=int(WorkflowStage.PROCESS_INSPECTION),
        inspection_type="PROCESS",
        inspector=inspector,
        request_qty=before_qty,
        good_qty=good_qty,
        defect_qty=defect_qty,
        grade_a_qty=grade_a_qty,
        grade_b_qty=grade_b_qty,
        grade_f_qty=grade_f_qty,
        result="PASS" if defect_qty == 0 else "PARTIAL",
        remark=remark,
        is_completed=True,
    )

    db.add(inspection)

    if attachment is not None and getattr(attachment, "filename", ""):
        db.flush()
        path, name = save_inspection_attachment(inspection.id, attachment)
        inspection.attachment_path = path
        inspection.attachment_name = name

    request = (
        db.query(WorkflowRequest)
        .filter(
            WorkflowRequest.workflow_no == workflow_no,
            WorkflowRequest.stage == int(
                WorkflowStage.PROCESS_INSPECTION_REQUEST
            ),
            WorkflowRequest.status == "WAITING",
        )
        .order_by(WorkflowRequest.id.desc())
        .first()
    )

    if request:
        request.status = "APPROVED"
        request.approved_qty = good_qty
        request.approved_by = inspector
        request.approved_at = datetime.now(ZoneInfo("Asia/Seoul"))

    item.current_stage = int(WorkflowStage.PROCESS_INSPECTION)
    item.current_department = "material"
    item.qty = good_qty
    item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

    add_remnant(
        db,
        workflow_no=workflow_no,
        stage=int(WorkflowStage.PROCESS_INSPECTION),
        department="material",
        item_code=item.item_code,
        item_name=item.item_name,
        lot=item.lot,
        qty=defect_qty,
        reason="DEFECT",
    )

    add_history(
        db,
        workflow_no=workflow_no,
        stage=int(WorkflowStage.PROCESS_INSPECTION),
        action="INSPECT",
        user_name=inspector,
        department="quality",
        before_qty=before_qty,
        after_qty=good_qty,
        remark=remark or (
            f"공정 검사 완료 (A {grade_a_qty} / B {grade_b_qty} / "
            f"F(불량) {grade_f_qty})"
        ),
    )

    add_notification(
        db,
        workflow_no=workflow_no,
        department="material",
        title="공정 검사 완료",
        message=(
            f"{workflow_no} 공정 검사가 완료되었습니다. "
            f"(A {grade_a_qty} / B {grade_b_qty} / F(불량) {grade_f_qty}) "
            f"자재 확인이 필요합니다."
        ),
        notification_type="INSPECTION",
    )

    db.commit()
    db.refresh(inspection)

    return inspection

def get_inspections(
    db: Session,
    workflow_no: str = "",
    inspection_type: str = ""
):
    query = db.query(WorkflowInspection)

    if workflow_no:
        query = query.filter(
            WorkflowInspection.workflow_no == workflow_no
        )

    if inspection_type:
        query = query.filter(
            WorkflowInspection.inspection_type == inspection_type
        )

    return (
        query
        .order_by(WorkflowInspection.id.desc())
        .all()
    )