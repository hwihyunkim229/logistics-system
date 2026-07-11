from sqlalchemy.orm import Session
from app.workflow.models.workflow_remnant import WorkflowRemnant
from app.workflow.models.workflow_item import WorkflowItem


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
):
    """
    잔존 자재 기록 생성 (commit은 호출자가 담당). qty가 0 이하면
    잔량이 없는 것이므로 아무것도 만들지 않는다.
    """

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
    )

    db.add(remnant)

    return remnant


def clear_remnants(
    db: Session,
    workflow_no: str,
    stage: int,
):
    """
    특정 단계의 잔존 기록 삭제 - 그 단계가 반려되어 재작업될 때
    호출한다. 재작업 결과에 따라 잔량이 다시 만들어진다.
    (commit은 호출자가 담당)
    """

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
    """
    특정 부서/사유/품목코드로 남아 있는 잔존 수량 합계 - 반제품 생산 적용에서
    이전에 못 쓰고 남은 같은 품목의 재고를 다음 생산에 합쳐 쓸 때
    (동일 품목이 다시 들어왔을 때) 가용 수량을 계산하기 위해 쓴다.
    """

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
    """
    특정 부서/사유/품목코드의 잔존 풀에서 qty만큼만 소모한다(오래된
    기록부터). 이번 생산에 새로 도착한 수량만으로 부족해서 기존
    잔존 풀까지 끌어다 쓸 때 호출한다.

    이전 버전은 풀 전체를 지우고 새 수량으로 한 건만 다시 만들었는데,
    그러면 실제로 안 건드려도 되는 여분까지 통째로 사라지고, 반려됐을
    때도 원래 있던 잔존 기록을 되살릴 방법이 없었다 - 필요한 만큼만
    줄이면 나머지는 그대로 남고, 소모한 만큼은 호출자가 이력에 남겨
    반려 시 정확히 복원할 수 있다.

    실제로 소모된 수량을 반환한다(풀에 남은 게 부족하면 있는 만큼만).
    (commit은 호출자가 담당)
    """

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
    """
    특정 workflow/단계의 잔존 기록을 삭제하면서 남아 있던 수량 합계를
    반환한다 - 세트 완료 때 잔존 풀로 보관됐던(POOL_STORE) 구성품을
    반려로 되살릴 때, 그 사이 후속 생산이 얼마를 이미 소모했든 지금
    남아 있는 만큼만 workflow 수량으로 되돌리기 위해 쓴다.
    (commit은 호출자가 담당)
    """

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
    """
    잔존 자재를 새 Workflow(1단계 구매 입고)로 재입고 처리한다.

    잔존 기록은 어느 단계에서 남았는지만 알려줄 뿐, 그 수량이
    실제로 다음 공정에 다시 투입될 방법이 없었다 - 이 함수는
    잔존 기록을 소진 처리하고 동일한 품목/LOT/수량으로 새 workflow를
    만들어 구매팀 페이지에서부터 다시 프로세스를 태울 수 있게 한다.
    (순환 import를 피하기 위해 WorkflowService는 함수 내부에서 가져온다)
    """

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

    # 잔존 기록을 먼저 지우고 커밋해서 소진 처리한다 - "재입고" 버튼이
    # 중복 클릭되거나 요청이 겹쳐도, 두 번째 호출은 이미 삭제된
    # 기록을 찾지 못해 위의 "찾을 수 없습니다" 오류로 안전하게
    # 끝나므로, 같은 잔량으로 workflow가 두 번 만들어지는 일이 없다.
    db.delete(remnant)
    db.commit()

    service = WorkflowService(db)

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
    """
    부서별 workflow_no -> 잔량 합계 dict (목록 테이블의 잔량 컬럼용)
    """

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
