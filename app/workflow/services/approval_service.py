from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_history import WorkflowHistory
from app.workflow.models.workflow_notification import WorkflowNotification
from app.workflow.models.workflow_stage import get_next_stage
from app.workflow.services.remnant_service import add_remnant

def approve_request(
    db: Session,
    request_id: int,
    approved_qty: int,
    approved_by: str,
):
    request = (
        db.query(WorkflowRequest)
        .filter(WorkflowRequest.id == request_id)
        .first()
    )

    if request is None:
        raise Exception("요청을 찾을 수 없습니다.")

    item = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.workflow_no == request.workflow_no
        )
        .first()
    )

    if item is None:
        raise Exception("Workflow를 찾을 수 없습니다.")

    if request.status != "WAITING":
        raise Exception("대기 상태의 요청만 승인할 수 있습니다.")

    if approved_qty < 1:
        raise Exception("승인 수량은 1개 이상이어야 합니다.")

    if approved_qty > item.qty:
        raise Exception(
            f"승인 수량이 보유 수량({item.qty})을 초과할 수 없습니다."
        )

    before_qty = item.qty
    remaining_qty = before_qty - approved_qty
    request.status = "APPROVED"
    request.approved_qty = approved_qty
    request.approved_by = approved_by
    request.approved_at = datetime.now(
        ZoneInfo("Asia/Seoul")
    )

    next_stage = get_next_stage(item.current_stage)

    if next_stage is not None:
        item.current_stage = int(next_stage)

    item.current_department = request.to_department
    item.qty = approved_qty
    item.process_qty = approved_qty
    item.updated_at = datetime.now(
        ZoneInfo("Asia/Seoul")
    )

    if remaining_qty > 0 and request.from_department in (
        "material",
        "production",
    ):
        add_remnant(
            db,
            workflow_no=item.workflow_no,
            stage=request.stage,
            department=request.from_department,
            item_code=item.item_code,
            item_name=item.item_name,
            lot=item.lot,
            qty=remaining_qty,
            reason="PARTIAL_APPROVAL",
        )

    history = WorkflowHistory(
        workflow_no=item.workflow_no,
        stage=item.current_stage,
        action="APPROVE",
        user_name=approved_by,
        department=request.to_department,
        before_qty=before_qty,
        after_qty=approved_qty,
        remark=(
            f"승인 완료 - 보유 수량 {before_qty} 중 {approved_qty}개 확정"
            f" (잔량 {remaining_qty})"
            if remaining_qty > 0
            else "승인 완료"
        ),
        result="SUCCESS",
    )

    db.add(history)

    notification = WorkflowNotification(
        workflow_no=item.workflow_no,
        department=request.to_department,
        title="승인 완료",
        message=(
            f"다음 단계로 진행할 수 있습니다. "
            f"(확정 수량: {approved_qty} EA)"
        ),
        notification_type="APPROVAL",
    )

    db.add(notification)
    db.commit()

    return item