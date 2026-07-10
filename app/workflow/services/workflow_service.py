from sqlalchemy.orm import Session
from app.workflow.services.request_service import create_request
from app.workflow.services.approval_service import approve_request
from app.workflow.services.history_service import add_history
from app.workflow.services.notification_service import add_notification
from app.workflow.services.remnant_service import (
    add_remnant,
    clear_remnants,
    remnant_qty_by_item,
    clear_remnants_by_item,
)
from app.workflow.config import (
    PRODUCTION_TRANSFORM,
    PACKAGING_TRANSFORM,
    PRODUCTION_COMPONENTS,
    PACKAGING_COMPONENTS,
)
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_inspection import WorkflowInspection
from app.workflow.models.workflow_history import WorkflowHistory
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    get_stage_name,
    get_previous_stage,
    get_department,
)
from datetime import datetime
from zoneinfo import ZoneInfo

MATERIAL_CONFIRM_STAGES = {
    int(WorkflowStage.QUALITY_INSPECTION):
        int(WorkflowStage.MATERIAL_CONFIRM_1),
    int(WorkflowStage.PRODUCTION_COMPLETE):
        int(WorkflowStage.MATERIAL_CONFIRM_2),
    int(WorkflowStage.PROCESS_INSPECTION):
        int(WorkflowStage.MATERIAL_CONFIRM_3),
    int(WorkflowStage.PACKAGING_COMPLETE):
        int(WorkflowStage.MATERIAL_FINAL_CONFIRM),
}

MATERIAL_REJECT_ROLLBACK = {
    int(WorkflowStage.QUALITY_INSPECTION):
        int(WorkflowStage.QUALITY_APPROVAL),
    int(WorkflowStage.PRODUCTION_COMPLETE):
        int(WorkflowStage.PRODUCTION_APPROVAL),
    int(WorkflowStage.PROCESS_INSPECTION):
        int(WorkflowStage.PROCESS_INSPECTION_REQUEST),
    int(WorkflowStage.PACKAGING_COMPLETE):
        int(WorkflowStage.PACKAGING_REQUEST),
}


class WorkflowService:

    def __init__(self, db: Session):
        self.db = db

    def _get_item(self, workflow_no: str):
        item = (
            self.db.query(WorkflowItem)
            .filter(WorkflowItem.workflow_no == workflow_no)
            .first()
        )

        if item is None:
            raise Exception("Workflow를 찾을 수 없습니다.")

        return item

    def request_quality(
        self,
        workflow_no: str,
        qty: int,
        requested_by: str,
        remark: str = "",
    ):

        return create_request(
            db=self.db,
            workflow_no=workflow_no,
            stage=2,
            request_type="QUALITY_REQUEST",
            from_department="purchase",
            to_department="quality",
            request_qty=qty,
            requested_by=requested_by,
            remark=remark,
        )

    def request_production(
        self,
        workflow_no: str,
        qty: int,
        requested_by: str,
        remark: str = "",
    ):

        return create_request(
            db=self.db,
            workflow_no=workflow_no,
            stage=6,
            request_type="PRODUCTION_REQUEST",
            from_department="material",
            to_department="production",
            request_qty=qty,
            requested_by=requested_by,
            remark=remark,
        )

    def request_process_inspection(
        self,
        workflow_no: str,
        qty: int,
        requested_by: str,
        remark: str = "",
    ):

        return create_request(
            db=self.db,
            workflow_no=workflow_no,
            stage=10,
            request_type="PROCESS_INSPECTION",
            from_department="material",
            to_department="quality",
            request_qty=qty,
            requested_by=requested_by,
            remark=remark,
        )

    def request_packaging(
        self,
        workflow_no: str,
        qty: int,
        requested_by: str,
        remark: str = "",
    ):

        return create_request(
            db=self.db,
            workflow_no=workflow_no,
            stage=13,
            request_type="PACKAGING_REQUEST",
            from_department="material",
            to_department="production",
            request_qty=qty,
            requested_by=requested_by,
            remark=remark,
        )

    def request_packaging_direct(
        self,
        workflow_no: str,
        qty: int,
        requested_by: str,
        remark: str = "",
    ):
        """
        CRADLE처럼 이미 반제품으로 구매되는 포장 구성품은 생산(조립)·
        공정검사 단계가 필요 없으므로, 자재 확인(5단계) 완료 후
        생산/공정검사 단계를 건너뛰고 곧바로 포장 요청(13단계)으로
        넘어간다.
        """

        return create_request(
            db=self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.PACKAGING_REQUEST),
            request_type="PACKAGING_REQUEST",
            from_department="material",
            to_department="production",
            request_qty=qty,
            requested_by=requested_by,
            remark=remark or "반제품 포장 요청 (생산/공정검사 생략)",
            next_stage=int(WorkflowStage.PACKAGING_REQUEST),
        )

    def approve(
        self,
        request_id: int,
        approved_qty: int,
        approved_by: str,
    ):

        return approve_request(
            db=self.db,
            request_id=request_id,
            approved_qty=approved_qty,
            approved_by=approved_by,
        )
    
    def create_workflow(
        self,
        item_code: str,
        item_name: str,
        lot: str,
        rev: str,
        qty: int,
        created_by: str,
        service_type: str = "",
        received_at=None,
    ):
        """
        Workflow 신규 생성
        """

        if not (lot or "").strip():
            raise Exception(
                "LOT는 필수 입력 항목입니다. 동일한 품목 코드라도 입고 "
                "건마다 LOT를 다르게 부여해야 합니다."
            )

        item_code = "".join((item_code or "").split())

        item = WorkflowItem(
            workflow_no="TEMP",
            item_code=item_code,
            item_name=item_name,
            lot=lot.strip(),
            rev=rev,
            qty=qty,
            initial_qty=qty,
            received_at=received_at or datetime.now(
                ZoneInfo("Asia/Seoul")
            ),
            current_stage=int(WorkflowStage.PURCHASE_RECEIVED),
            current_department="purchase",
            status="IN_PROGRESS",
            created_by=created_by,
            service_type=service_type,
        )

        self.db.add(item)

        self.db.flush()

        today = datetime.now().strftime("%Y%m%d")
        item.workflow_no = f"WF-{today}-{item.id:06d}"

        add_history(
            self.db,
            workflow_no=item.workflow_no,
            stage=int(WorkflowStage.PURCHASE_RECEIVED),
            action="CREATE",
            user_name=created_by,
            department="purchase",
            before_qty=qty,
            after_qty=qty,
            remark=f"구매 입고 등록 ({item_code})",
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def material_confirm(
        self,
        workflow_no: str,
        confirmed_by: str,
        remark: str = "",
    ):
        """
        자재 확인/승인 (5, 9, 12, 15단계) - 이전 단계 결과를 자재팀이
        확인하고 다음 작업으로 넘긴다.
        """

        item = self._get_item(workflow_no)

        next_stage = MATERIAL_CONFIRM_STAGES.get(item.current_stage)

        if next_stage is None:
            raise Exception(
                f"자재 확인을 진행할 수 없는 단계입니다. "
                f"(현재: {get_stage_name(item.current_stage)})"
            )

        item.current_stage = next_stage
        item.current_department = "material"
        item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

        stage_name = get_stage_name(next_stage)

        add_history(
            self.db,
            workflow_no=workflow_no,
            stage=next_stage,
            action="CONFIRM",
            user_name=confirmed_by,
            department="material",
            before_qty=item.qty,
            after_qty=item.qty,
            remark=remark or f"{stage_name} 완료",
        )

        add_notification(
            self.db,
            workflow_no=workflow_no,
            department="material",
            title=f"{stage_name} 완료",
            message=f"{workflow_no} {stage_name}이(가) 완료되었습니다.",
            notification_type="CONFIRM",
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def material_reject(
        self,
        workflow_no: str,
        rejected_by: str,
        remark: str = "",
    ):
        """
        자재 확인 단계에서 반려 - 직전 부서(품질/생산)가 작업을 다시
        하도록 해당 부서의 대기 단계로 되돌린다.
        """

        item = self._get_item(workflow_no)

        redone_stage = item.current_stage
        rollback_stage = MATERIAL_REJECT_ROLLBACK.get(redone_stage)

        if rollback_stage is None:
            raise Exception(
                f"반려할 수 없는 단계입니다. "
                f"(현재: {get_stage_name(item.current_stage)})"
            )

        redo_department = get_department(rollback_stage + 1)
        before_qty = item.qty
        restored_qty = None

        if redone_stage in (
            int(WorkflowStage.QUALITY_INSPECTION),
            int(WorkflowStage.PROCESS_INSPECTION),
        ):
            inspection_type = (
                "INCOMING"
                if redone_stage == int(WorkflowStage.QUALITY_INSPECTION)
                else "PROCESS"
            )

            last_inspection = (
                self.db.query(WorkflowInspection)
                .filter(
                    WorkflowInspection.workflow_no == workflow_no,
                    WorkflowInspection.inspection_type == inspection_type,
                )
                .order_by(WorkflowInspection.id.desc())
                .first()
            )

            if last_inspection:
                restored_qty = last_inspection.request_qty

        else:
            last_complete = (
                self.db.query(WorkflowHistory)
                .filter(
                    WorkflowHistory.workflow_no == workflow_no,
                    WorkflowHistory.stage == redone_stage,
                    WorkflowHistory.action == "COMPLETE",
                )
                .order_by(WorkflowHistory.id.desc())
                .first()
            )

            if last_complete:
                restored_qty = last_complete.before_qty

        if restored_qty is not None:
            item.qty = restored_qty

        clear_remnants(self.db, workflow_no, redone_stage)

        if redone_stage in (
            int(WorkflowStage.PRODUCTION_COMPLETE),
            int(WorkflowStage.PACKAGING_COMPLETE),
        ):
            if item.prev_item_code:
                item.item_code = item.prev_item_code
                item.item_name = item.prev_item_name
                item.lot = item.prev_lot
                item.prev_item_code = None
                item.prev_item_name = None
                item.prev_lot = None

            merged_components = (
                self.db.query(WorkflowItem)
                .filter(
                    WorkflowItem.merged_into == workflow_no,
                    WorkflowItem.status == "MERGED",
                    WorkflowItem.current_stage == redone_stage,
                )
                .all()
            )

            for comp in merged_components:
                consume_history = (
                    self.db.query(WorkflowHistory)
                    .filter(
                        WorkflowHistory.workflow_no == comp.workflow_no,
                        WorkflowHistory.stage == redone_stage,
                        WorkflowHistory.action == "CONSUME",
                    )
                    .order_by(WorkflowHistory.id.desc())
                    .first()
                )

                comp.qty = (
                    consume_history.before_qty
                    if consume_history
                    else comp.qty
                )
                comp.status = "IN_PROGRESS"
                comp.merged_into = None
                comp.current_stage = rollback_stage
                comp.current_department = redo_department
                comp.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

                clear_remnants(self.db, comp.workflow_no, redone_stage)

                if redone_stage == int(WorkflowStage.PACKAGING_COMPLETE):
                    comp_request = (
                        self.db.query(WorkflowRequest)
                        .filter(
                            WorkflowRequest.workflow_no == comp.workflow_no,
                            WorkflowRequest.stage == int(
                                WorkflowStage.PACKAGING_REQUEST
                            ),
                            WorkflowRequest.status == "APPROVED",
                        )
                        .order_by(WorkflowRequest.id.desc())
                        .first()
                    )

                    if comp_request:
                        comp_request.status = "WAITING"
                        comp_request.approved_qty = 0
                        comp_request.approved_by = None
                        comp_request.approved_at = None

                add_history(
                    self.db,
                    workflow_no=comp.workflow_no,
                    stage=rollback_stage,
                    action="REJECT",
                    user_name=rejected_by,
                    department="material",
                    before_qty=0,
                    after_qty=comp.qty,
                    remark=f"세트 반려로 구성품 복원 (수량 {comp.qty})",
                    result="REJECTED",
                )

        reopen_request_stage = {
            int(WorkflowStage.PROCESS_INSPECTION):
                int(WorkflowStage.PROCESS_INSPECTION_REQUEST),
            int(WorkflowStage.PACKAGING_COMPLETE):
                int(WorkflowStage.PACKAGING_REQUEST),
        }.get(redone_stage)

        if reopen_request_stage is not None:
            approved_request = (
                self.db.query(WorkflowRequest)
                .filter(
                    WorkflowRequest.workflow_no == workflow_no,
                    WorkflowRequest.stage == reopen_request_stage,
                    WorkflowRequest.status == "APPROVED",
                )
                .order_by(WorkflowRequest.id.desc())
                .first()
            )

            if approved_request:
                approved_request.status = "WAITING"
                approved_request.approved_qty = 0
                approved_request.approved_by = None
                approved_request.approved_at = None

            else:
                to_department = get_department(reopen_request_stage + 1)

                self.db.add(WorkflowRequest(
                    workflow_no=workflow_no,
                    stage=reopen_request_stage,
                    request_type=(
                        "PROCESS_INSPECTION"
                        if reopen_request_stage == int(
                            WorkflowStage.PROCESS_INSPECTION_REQUEST
                        )
                        else "PACKAGING_REQUEST"
                    ),
                    from_department="material",
                    to_department=to_department,
                    request_qty=item.qty,
                    requested_by=rejected_by,
                    status="WAITING",
                    remark=remark or "자재팀 반려",
                    service_type=item.service_type,
                    item_code=item.item_code,
                    item_name=item.item_name,
                ))

        item.current_stage = rollback_stage
        item.current_department = redo_department
        item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

        add_history(
            self.db,
            workflow_no=workflow_no,
            stage=rollback_stage,
            action="REJECT",
            user_name=rejected_by,
            department="material",
            before_qty=before_qty,
            after_qty=item.qty,
            remark=(
                (remark or "자재 확인 반려")
                + f" (재작업 수량 {item.qty}로 복원)"
            ),
            result="REJECTED",
        )

        add_notification(
            self.db,
            workflow_no=workflow_no,
            department=redo_department,
            title="자재 확인 반려",
            message=(
                f"{workflow_no} 결과가 자재팀에서 반려되었습니다. "
                f"재작업이 필요합니다."
                + (f" 사유: {remark}" if remark else "")
            ),
            notification_type="REJECT",
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def complete_production(
        self,
        workflow_no: str,
        completed_by: str,
        good_qty: int,
        defect_qty: int,
        lot: str = "",
        remark: str = "",
    ):
        """
        생산 완료 등록 (8단계) - 양품 수량이 이후 단계의 기준 수량이
        되고, level3 원자재(INNER/PBA/TOP COVER/OUTER)는 level2
        (CART_Ring)로 품목코드/품명이 자동 변환된다. LOT는 생산팀이
        직접 입력한다.
        """

        item = self._get_item(workflow_no)

        if item.current_stage != int(WorkflowStage.PRODUCTION_APPROVAL):
            raise Exception(
                f"생산 완료를 등록할 수 없는 단계입니다. "
                f"(현재: {get_stage_name(item.current_stage)})"
            )

        if PRODUCTION_TRANSFORM.get(item.item_code):
            raise Exception(
                "반제품 생산 적용 대상 구성품입니다. 구성품 4종이 모두 도착한 뒤 "
                "반제품 생산 적용 완료로 진행해주세요."
            )

        before_qty = item.qty
        before_code = item.item_code
        before_name = item.item_name

        add_remnant(
            self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.PRODUCTION_COMPLETE),
            department="material",
            item_code=before_code,
            item_name=before_name,
            lot=item.lot,
            qty=defect_qty,
            reason="DEFECT",
        )

        transform = PRODUCTION_TRANSFORM.get(item.item_code)
        transform_note = ""

        if transform:
            if not (lot or "").strip():
                raise Exception("생산 완료 시 LOT를 입력해야 합니다.")

            item.prev_item_code = item.item_code
            item.prev_item_name = item.item_name
            item.prev_lot = item.lot

            item.item_code, item.item_name = transform
            item.lot = lot.strip()

            transform_note = (
                f" / 품목 변환: {before_code} -> {item.item_code}"
                f" (LOT {item.lot})"
            )

        elif (lot or "").strip():
            item.lot = lot.strip()

        item.current_stage = int(WorkflowStage.PRODUCTION_COMPLETE)
        item.current_department = "material"
        item.qty = good_qty
        item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

        add_history(
            self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.PRODUCTION_COMPLETE),
            action="COMPLETE",
            user_name=completed_by,
            department="production",
            before_qty=before_qty,
            after_qty=good_qty,
            remark=(
                remark
                or f"생산 완료 (양품 {good_qty} / 불량 {defect_qty})"
            ) + transform_note,
        )

        add_notification(
            self.db,
            workflow_no=workflow_no,
            department="material",
            title="생산 완료",
            message=(
                f"{workflow_no} 생산이 완료되었습니다. "
                f"(양품 {good_qty} / 불량 {defect_qty}) 자재 확인이 필요합니다."
            ),
            notification_type="PRODUCTION",
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def complete_packaging(
        self,
        workflow_no: str,
        completed_by: str,
        good_qty: int,
        defect_qty: int,
        lot: str = "",
        remark: str = "",
    ):
        """
        포장 완료 등록 (14단계) - 포장 요청(13단계) 대기 요청을 함께
        완료 처리하고, level2(RING/CRADLE)는 level1(CART PLATFORM
        IEM)로 품목코드/품명이 자동 변환된다. LOT는 생산팀이 직접
        입력한다.
        """

        item = self._get_item(workflow_no)

        if item.current_stage != int(WorkflowStage.PACKAGING_REQUEST):
            raise Exception(
                f"포장 완료를 등록할 수 없는 단계입니다. "
                f"(현재: {get_stage_name(item.current_stage)})"
            )

        if PACKAGING_TRANSFORM.get(item.item_code):
            raise Exception(
                "제품 포장 적용 대상 구성품입니다. 구성품(RING/CRADLE)이 모두 "
                "도착한 뒤 제품 포장 적용 완료로 진행해주세요."
            )

        before_qty = item.qty
        before_code = item.item_code
        before_name = item.item_name

        request = (
            self.db.query(WorkflowRequest)
            .filter(
                WorkflowRequest.workflow_no == workflow_no,
                WorkflowRequest.stage == int(
                    WorkflowStage.PACKAGING_REQUEST
                ),
                WorkflowRequest.status == "WAITING",
            )
            .order_by(WorkflowRequest.id.desc())
            .first()
        )

        if request:
            request.status = "APPROVED"
            request.approved_qty = good_qty
            request.approved_by = completed_by
            request.approved_at = datetime.now(ZoneInfo("Asia/Seoul"))

        add_remnant(
            self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.PACKAGING_COMPLETE),
            department="material",
            item_code=before_code,
            item_name=before_name,
            lot=item.lot,
            qty=defect_qty,
            reason="DEFECT",
        )

        transform = PACKAGING_TRANSFORM.get(item.item_code)
        transform_note = ""

        if transform:
            if not (lot or "").strip():
                raise Exception("포장 완료 시 LOT를 입력해야 합니다.")

            item.prev_item_code = item.item_code
            item.prev_item_name = item.item_name
            item.prev_lot = item.lot
            item.item_code, item.item_name = transform
            item.lot = lot.strip()

            transform_note = (
                f" / 품목 변환: {before_code} -> {item.item_code}"
                f" (LOT {item.lot})"
            )

        elif (lot or "").strip():
            item.lot = lot.strip()

        item.current_stage = int(WorkflowStage.PACKAGING_COMPLETE)
        item.current_department = "material"
        item.qty = good_qty
        item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

        add_history(
            self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.PACKAGING_COMPLETE),
            action="COMPLETE",
            user_name=completed_by,
            department="production",
            before_qty=before_qty,
            after_qty=good_qty,
            remark=(
                remark
                or f"포장 완료 (양품 {good_qty} / 불량 {defect_qty})"
            ) + transform_note,
        )

        add_notification(
            self.db,
            workflow_no=workflow_no,
            department="material",
            title="포장 완료",
            message=(
                f"{workflow_no} 포장이 완료되었습니다. "
                f"(양품 {good_qty} / 불량 {defect_qty}) 최종 확인이 필요합니다."
            ),
            notification_type="PACKAGING",
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def _complete_set(
        self,
        target_code: str,
        produced_qty: int,
        lot: str,
        defects: dict,
        completed_by: str,
        remark: str,
        mode: str,
    ):
        """
        반제품 생산 적용/포장 공통 처리.

        구성품(생산: level3 4종 / 포장: level2 2종)이 전부 해당 단계에
        도착해 있어야 하며, 생산 수량은 (구성품 수량 - 구성품 불량)의
        최소값을 넘을 수 없다. 각 구성품의 불량은 DEFECT, 세트에
        쓰이지 못한 정상 수량은 SET_LEFTOVER 잔존으로 남는다.
        구성품 중 대표(가장 먼저 등록된) workflow가 결과물(level2/
        level1)로 변환되어 이어지고, 나머지는 MERGED 상태로 종료된다.
        """

        if mode == "production":
            components_map = PRODUCTION_COMPONENTS
            wait_stage = int(WorkflowStage.PRODUCTION_APPROVAL)
            done_stage = int(WorkflowStage.PRODUCTION_COMPLETE)
            transform_map = PRODUCTION_TRANSFORM
            action_label = "반제품 생산 적용"
        else:
            components_map = PACKAGING_COMPONENTS
            wait_stage = int(WorkflowStage.PACKAGING_REQUEST)
            done_stage = int(WorkflowStage.PACKAGING_COMPLETE)
            transform_map = PACKAGING_TRANSFORM
            action_label = "제품 포장 적용"

        required_codes = components_map.get(target_code)

        if not required_codes:
            raise Exception("세트 구성 정보를 찾을 수 없는 품목입니다.")

        if not (lot or "").strip():
            raise Exception(f"{action_label} 완료 시 LOT를 입력해야 합니다.")

        components = (
            self.db.query(WorkflowItem)
            .filter(
                WorkflowItem.item_code.in_(required_codes),
                WorkflowItem.current_stage == wait_stage,
                WorkflowItem.status == "IN_PROGRESS",
            )
            .order_by(WorkflowItem.id.asc())
            .all()
        )

        by_code = {}

        for comp in components:
            by_code.setdefault(comp.item_code, []).append(comp)

        missing = [c for c in required_codes if c not in by_code]

        if missing:
            raise Exception(
                "구성품이 아직 준비되지 않았습니다: " + ", ".join(missing)
            )

        duplicated = [c for c, rows in by_code.items() if len(rows) > 1]

        if duplicated:
            raise Exception(
                "동일 구성품 workflow가 2건 이상 있습니다: "
                + ", ".join(duplicated)
            )

        picked = [by_code[c][0] for c in required_codes]

        leftover_pool = {
            comp.item_code: remnant_qty_by_item(
                self.db,
                department="production",
                reason="SET_LEFTOVER",
                item_code=comp.item_code,
            )
            for comp in picked
        }

        usable = {}

        for comp in picked:
            defect = int(defects.get(comp.workflow_no, 0) or 0)

            if defect < 0 or defect > comp.qty:
                raise Exception(
                    f"{comp.item_code} 불량 수량이 올바르지 않습니다."
                )

            usable[comp.workflow_no] = (
                comp.qty - defect + leftover_pool.get(comp.item_code, 0)
            )

        max_producible = min(usable.values())

        if produced_qty < 1:
            raise Exception("생산 수량은 1개 이상이어야 합니다.")

        if produced_qty > max_producible:
            raise Exception(
                f"생산 수량이 구성품 가용 수량을 초과했습니다. "
                f"(최대 {max_producible})"
            )

        primary = picked[0]
        target_name = transform_map[primary.item_code][1]
        now = datetime.now(ZoneInfo("Asia/Seoul"))

        for comp in picked:
            defect = int(defects.get(comp.workflow_no, 0) or 0)
            leftover = usable[comp.workflow_no] - produced_qty

            add_remnant(
                self.db,
                workflow_no=comp.workflow_no,
                stage=done_stage,
                department="material",
                item_code=comp.item_code,
                item_name=comp.item_name,
                lot=comp.lot,
                qty=defect,
                reason="DEFECT",
            )

            clear_remnants_by_item(
                self.db,
                department="production",
                reason="SET_LEFTOVER",
                item_code=comp.item_code,
            )

            add_remnant(
                self.db,
                workflow_no=comp.workflow_no,
                stage=done_stage,
                department="production",
                item_code=comp.item_code,
                item_name=comp.item_name,
                lot=comp.lot,
                qty=leftover,
                reason="SET_LEFTOVER",
            )

            if mode == "packaging":
                waiting = (
                    self.db.query(WorkflowRequest)
                    .filter(
                        WorkflowRequest.workflow_no == comp.workflow_no,
                        WorkflowRequest.stage == wait_stage,
                        WorkflowRequest.status == "WAITING",
                    )
                    .order_by(WorkflowRequest.id.desc())
                    .first()
                )

                if waiting:
                    waiting.status = "APPROVED"
                    waiting.approved_qty = produced_qty
                    waiting.approved_by = completed_by
                    waiting.approved_at = now

            if comp is primary:
                continue

            add_history(
                self.db,
                workflow_no=comp.workflow_no,
                stage=done_stage,
                action="CONSUME",
                user_name=completed_by,
                department="production",
                before_qty=comp.qty,
                after_qty=0,
                remark=(
                    f"{action_label} 소모 -> {target_code}"
                    f" (대표 {primary.workflow_no})"
                ),
            )

            comp.status = "MERGED"
            comp.merged_into = primary.workflow_no
            comp.qty = 0
            comp.current_stage = done_stage
            comp.updated_at = now

        primary_before_qty = primary.qty
        primary.prev_item_code = primary.item_code
        primary.prev_item_name = primary.item_name
        primary.prev_lot = primary.lot
        primary.item_code = target_code
        primary.item_name = target_name
        primary.lot = lot.strip()
        primary.qty = produced_qty
        primary.current_stage = done_stage
        primary.current_department = "material"
        primary.updated_at = now

        add_history(
            self.db,
            workflow_no=primary.workflow_no,
            stage=done_stage,
            action="COMPLETE",
            user_name=completed_by,
            department="production",
            before_qty=primary_before_qty,
            after_qty=produced_qty,
            remark=(
                (remark or f"{action_label} 완료 ({produced_qty} EA)")
                + f" / 품목 변환: {primary.prev_item_code} -> {target_code}"
                + f" (LOT {primary.lot})"
                + " / 구성품: "
                + ", ".join(c.workflow_no for c in picked)
            ),
        )

        add_notification(
            self.db,
            workflow_no=primary.workflow_no,
            department="material",
            title=f"{action_label} 완료",
            message=(
                f"{primary.workflow_no} {action_label}이 완료되었습니다. "
                f"({target_name} {produced_qty} EA) 자재 확인이 필요합니다."
            ),
            notification_type=(
                "PRODUCTION" if mode == "production" else "PACKAGING"
            ),
        )

        self.db.commit()
        self.db.refresh(primary)

        return primary

    def complete_production_set(
        self,
        target_code: str,
        produced_qty: int,
        lot: str,
        defects: dict,
        completed_by: str,
        remark: str = "",
    ):
        return self._complete_set(
            target_code=target_code,
            produced_qty=produced_qty,
            lot=lot,
            defects=defects,
            completed_by=completed_by,
            remark=remark,
            mode="production",
        )

    def complete_packaging_set(
        self,
        target_code: str,
        produced_qty: int,
        lot: str,
        defects: dict,
        completed_by: str,
        remark: str = "",
    ):
        return self._complete_set(
            target_code=target_code,
            produced_qty=produced_qty,
            lot=lot,
            defects=defects,
            completed_by=completed_by,
            remark=remark,
            mode="packaging",
        )

    def ship_service(
        self,
        workflow_no: str,
        shipped_by: str,
        ship_qty: int,
        remark: str = "",
    ):
        """
        제품 출고 (16단계) - Workflow를 완료 상태로 전환한다.
        """

        item = self._get_item(workflow_no)

        if item.current_stage != int(WorkflowStage.MATERIAL_FINAL_CONFIRM):
            raise Exception(
                f"제품 출고를 진행할 수 없는 단계입니다. "
                f"(현재: {get_stage_name(item.current_stage)})"
            )

        if ship_qty < 1 or ship_qty > item.qty:
            raise Exception("출고 수량이 올바르지 않습니다.")

        before_qty = item.qty

        add_remnant(
            self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.SERVICE_SHIPMENT),
            department="material",
            item_code=item.item_code,
            item_name=item.item_name,
            lot=item.lot,
            qty=before_qty - ship_qty,
            reason="PARTIAL_SHIP",
        )

        item.current_stage = int(WorkflowStage.SERVICE_SHIPMENT)
        item.current_department = "material"
        item.qty = ship_qty
        item.status = "COMPLETED"
        item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

        add_history(
            self.db,
            workflow_no=workflow_no,
            stage=int(WorkflowStage.SERVICE_SHIPMENT),
            action="SHIP",
            user_name=shipped_by,
            department="material",
            before_qty=before_qty,
            after_qty=ship_qty,
            remark=remark or f"제품 출고 완료 ({ship_qty} EA)",
        )

        add_notification(
            self.db,
            workflow_no=workflow_no,
            department="purchase",
            title="제품 출고 완료",
            message=f"{workflow_no} 제품 출고가 완료되었습니다. ({ship_qty} EA)",
            notification_type="SHIPMENT",
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def reject(
        self,
        request_id: int,
        rejected_by: str,
        remark: str = "",
    ):
        """
        요청 반려 - 요청을 REJECTED로 바꾸고 Workflow 단계를 요청
        이전으로 되돌려서 요청 부서가 다시 보낼 수 있게 한다.
        """

        request = (
            self.db.query(WorkflowRequest)
            .filter(WorkflowRequest.id == request_id)
            .first()
        )

        if request is None:
            raise Exception("요청을 찾을 수 없습니다.")

        if request.status != "WAITING":
            raise Exception("대기 상태의 요청만 반려할 수 있습니다.")

        item = self._get_item(request.workflow_no)

        request.status = "REJECTED"
        request.approved_by = rejected_by
        request.approved_at = datetime.now(ZoneInfo("Asia/Seoul"))

        previous_stage = get_previous_stage(request.stage)

        if previous_stage is not None:
            item.current_stage = int(previous_stage)
            item.current_department = get_department(int(previous_stage))

        item.updated_at = datetime.now(ZoneInfo("Asia/Seoul"))

        add_history(
            self.db,
            workflow_no=item.workflow_no,
            stage=request.stage,
            action="REJECT",
            user_name=rejected_by,
            department=request.to_department,
            before_qty=request.request_qty,
            after_qty=request.request_qty,
            remark=remark or "반려",
            result="REJECTED",
        )

        add_notification(
            self.db,
            workflow_no=item.workflow_no,
            department=request.from_department,
            title="요청 반려",
            message=(
                f"{item.workflow_no} 요청이 반려되었습니다."
                + (f" 사유: {remark}" if remark else "")
            ),
            notification_type="REJECT",
        )

        self.db.commit()
        self.db.refresh(item)

        return item