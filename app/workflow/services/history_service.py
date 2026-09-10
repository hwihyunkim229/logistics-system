from app.utils.filters import as_values
from sqlalchemy.orm import Session
from app.workflow.models.workflow_history import WorkflowHistory

def add_history(
    db: Session,
    workflow_no: str,
    stage: int,
    action: str,
    user_name: str,
    department: str,
    before_qty: int,
    after_qty: int,
    remark: str = "",
    result: str = "SUCCESS",
):
    history = WorkflowHistory(
        workflow_no=workflow_no,
        stage=stage,
        action=action,
        user_name=user_name,
        department=department,
        before_qty=before_qty,
        after_qty=after_qty,
        remark=remark,
        result=result,
    )

    db.add(history)

    return history

def get_histories(
    db: Session,
    workflow_no: str = "",
    department: str = "",
    limit: int = 200,
):
    query = db.query(WorkflowHistory)

    if workflow_no:
        query = query.filter(
            WorkflowHistory.workflow_no == workflow_no
        )

    if department:
        query = query.filter(
            WorkflowHistory.department.in_(as_values(department))
        )

    return (
        query
        .order_by(WorkflowHistory.id.desc())
        .limit(limit)
        .all()
    )