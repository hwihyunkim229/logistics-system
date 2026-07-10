# Base.metadata.create_all()이 workflow 테이블 전체를 인식하려면 모든
# 모델이 import되어 있어야 한다 - 라우터가 직접 안 쓰는 모델(예:
# WorkflowInspection)도 여기서 한 번에 등록한다.
from app.workflow.models.workflow_item import WorkflowItem
from app.workflow.models.workflow_request import WorkflowRequest
from app.workflow.models.workflow_inspection import WorkflowInspection
from app.workflow.models.workflow_history import WorkflowHistory
from app.workflow.models.workflow_notification import WorkflowNotification
from app.workflow.models.workflow_remnant import WorkflowRemnant
from app.workflow.models.workflow_stage import (
    WorkflowStage,
    STAGE_INFO,
    TOTAL_STAGE,
)
