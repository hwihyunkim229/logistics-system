from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_history import WorkflowHistory
from app.workflow.models.workflow_notification import WorkflowNotification
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_stage import get_next_stage
from app.workflow.models.workflow_item import WorkflowItem

def create_request(
    db: Session,
    workflow_no: str,
    stage: int,
    request_type: str,
    from_department: str,
    to_department: str,
    request_qty: int,
    requested_by: str,
    remark: str = "",
    next_stage: int = None,
):
    """
    새로운 Workflow 요청 생성
    """

    item = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.workflow_no == workflow_no
        )
        .first()
    )

    if item is None:
        raise ValueError("Workflow를 찾을 수 없습니다.")

    request = WorkflowRequest(
        workflow_no=workflow_no,
        stage=stage,
        request_type=request_type,
        from_department=from_department,
        to_department=to_department,
        request_qty=request_qty,
        requested_by=requested_by,
        status="WAITING",
        remark=remark,
        service_type=item.service_type,
        item_code=item.item_code,
        item_name=item.item_name
    )

    db.add(request)

    history = WorkflowHistory(
        workflow_no=workflow_no,
        stage=stage,
        action="REQUEST",
        department=from_department,
        user_name=requested_by,
        before_qty=request_qty,
        after_qty=request_qty,
        remark=remark,
        result="SUCCESS",
    )

    db.add(history)

    notification = WorkflowNotification(
        workflow_no=workflow_no,
        department=to_department,
        title="새로운 요청",
        message=f"{from_department}에서 새로운 요청이 도착했습니다.",
        notification_type=request_type,
    )

    item = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.workflow_no == workflow_no
        )
        .first()
    )

    if item:
        # 반제품(CRADLE 등)처럼 중간 단계를 건너뛰어야 하는 요청은
        # 호출자가 next_stage를 직접 지정한다 - 지정이 없으면 원래
        # 대로 다음 단계(+1)로 진행한다.
        target_stage = (
            next_stage
            if next_stage is not None
            else get_next_stage(item.current_stage)
        )

        if target_stage:
            item.current_stage = int(target_stage)

        item.current_department = to_department

        item.updated_at = datetime.now(
            ZoneInfo("Asia/Seoul")
        )

    db.add(notification)
    db.commit()
    db.refresh(request)

    return request