from enum import IntEnum

class WorkflowStage(IntEnum):
    PURCHASE_RECEIVED = 1
    QUALITY_REQUEST = 2
    QUALITY_APPROVAL = 3
    QUALITY_INSPECTION = 4
    MATERIAL_CONFIRM_1 = 5
    PRODUCTION_REQUEST = 6
    PRODUCTION_APPROVAL = 7
    PRODUCTION_COMPLETE = 8
    MATERIAL_CONFIRM_2 = 9
    PROCESS_INSPECTION_REQUEST = 10
    PROCESS_INSPECTION = 11
    MATERIAL_CONFIRM_3 = 12
    PACKAGING_REQUEST = 13
    PACKAGING_COMPLETE = 14
    MATERIAL_FINAL_CONFIRM = 15
    SERVICE_SHIPMENT = 16

STAGE_INFO = {
    WorkflowStage.PURCHASE_RECEIVED: {
        "name": "구매 입고",
        "department": "purchase",
        "next_department": "purchase",
    },

    WorkflowStage.QUALITY_REQUEST: {
        "name": "수입 검사 의뢰",
        "department": "purchase",
        "next_department": "quality",
    },

    WorkflowStage.QUALITY_APPROVAL: {
        "name": "품질 입고 승인",
        "department": "quality",
        "next_department": "quality",
    },

    WorkflowStage.QUALITY_INSPECTION: {
        "name": "품질 수입 검사",
        "department": "quality",
        "next_department": "material",
    },

    WorkflowStage.MATERIAL_CONFIRM_1: {
        "name": "자재 확인",
        "department": "material",
        "next_department": "material",
    },

    WorkflowStage.PRODUCTION_REQUEST: {
        "name": "생산 요청",
        "department": "material",
        "next_department": "production",
    },

    WorkflowStage.PRODUCTION_APPROVAL: {
        "name": "생산 승인",
        "department": "production",
        "next_department": "production",
    },

    WorkflowStage.PRODUCTION_COMPLETE: {
        "name": "생산 완료",
        "department": "production",
        "next_department": "material",
    },

    WorkflowStage.MATERIAL_CONFIRM_2: {
        "name": "자재 확인",
        "department": "material",
        "next_department": "material",
    },

    WorkflowStage.PROCESS_INSPECTION_REQUEST: {
        "name": "공정 검사 의뢰",
        "department": "material",
        "next_department": "quality",
    },

    WorkflowStage.PROCESS_INSPECTION: {
        "name": "공정 검사",
        "department": "quality",
        "next_department": "material",
    },

    WorkflowStage.MATERIAL_CONFIRM_3: {
        "name": "자재 확인",
        "department": "material",
        "next_department": "material",
    },

    WorkflowStage.PACKAGING_REQUEST: {
        "name": "포장 요청",
        "department": "material",
        "next_department": "production",
    },

    WorkflowStage.PACKAGING_COMPLETE: {
        "name": "포장 완료",
        "department": "production",
        "next_department": "material",
    },

    WorkflowStage.MATERIAL_FINAL_CONFIRM: {
        "name": "자재 최종 확인",
        "department": "material",
        "next_department": "material",
    },

    WorkflowStage.SERVICE_SHIPMENT: {
        "name": "제품 출고",
        "department": "material",
        "next_department": None,
    },
}

TOTAL_STAGE = len(WorkflowStage)

def get_stage_name(stage: int):
    return STAGE_INFO[WorkflowStage(stage)]["name"]

def get_department(stage: int):
    return STAGE_INFO[WorkflowStage(stage)]["department"]

def get_next_department(stage: int):
    return STAGE_INFO[WorkflowStage(stage)]["next_department"]

def get_next_stage(stage: int):

    stage = WorkflowStage(stage)

    if stage == WorkflowStage.SERVICE_SHIPMENT:
        return None

    return WorkflowStage(stage + 1)

def get_previous_stage(stage: int):

    stage = WorkflowStage(stage)

    if stage == WorkflowStage.PURCHASE_RECEIVED:
        return None

    return WorkflowStage(stage - 1)