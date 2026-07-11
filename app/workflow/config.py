DEPARTMENT_NAMES = {
    "purchase": "구매팀",
    "quality": "품질팀",
    "material": "자재팀",
    "production": "생산팀",
}

REQUEST_TYPE_NAMES = {
    "QUALITY_REQUEST": "수입 검사 의뢰",
    "PRODUCTION_REQUEST": "생산 요청",
    "PROCESS_INSPECTION": "공정 검사 의뢰",
    "PACKAGING_REQUEST": "포장 요청",
}

STATUS_NAMES = {
    "WAITING": "대기",
    "APPROVED": "승인",
    "REJECTED": "반려",
    "IN_PROGRESS": "진행중",
    "COMPLETED": "완료",
}

ACTION_NAMES = {
    "CREATE": "등록",
    "REQUEST": "요청",
    "APPROVE": "승인",
    "REJECT": "반려",
    "INSPECT": "검사",
    "CONFIRM": "확인",
    "COMPLETE": "완료",
    "SHIP": "출고",
}

REMNANT_REASON_NAMES = {
    "PARTIAL_APPROVAL": "부분 승인 잔량",
    "DEFECT": "불량",
    "PARTIAL_REQUEST": "부분 요청 잔량",
    "PARTIAL_SHIP": "부분 출고 잔량",
    "SET_LEFTOVER": "세트 미사용 잔량",
}

def _build_level_transforms():
    production = {}
    packaging = {}
    production_components = {}
    packaging_components = {}

    for i, size in enumerate(range(8, 14)):
        level1_code = f"SL-P-PD-{110 + i:05d}"
        level1_name = f"CART PLATFORM IEM_size {size}"

        cradle_code = f"SL-P-HG-{92 + i:05d}"
        ring_code = f"SL-P-HG-{148 + i:05d}"
        ring_name = f"CART_Ring_Rev.2D_size {size}"

        level3_codes = [
            f"SL-M-RM-{199 + i:05d}",
            f"SL-H-AS-{87 + i:05d}",
            f"SL-M-RM-{286 + i:05d}",
            f"SL-M-RM-{339 + i:05d}",
        ]

        for code in level3_codes:
            production[code] = (ring_code, ring_name)

        packaging[ring_code] = (level1_code, level1_name)
        packaging[cradle_code] = (level1_code, level1_name)

        production_components[ring_code] = level3_codes
        packaging_components[level1_code] = [ring_code, cradle_code]

    return (
        production,
        packaging,
        production_components,
        packaging_components,
    )


(
    PRODUCTION_TRANSFORM,
    PACKAGING_TRANSFORM,
    PRODUCTION_COMPONENTS,
    PACKAGING_COMPONENTS,
) = _build_level_transforms()

PREMADE_PACKAGING_CODES = {
    code
    for codes in PACKAGING_COMPONENTS.values()
    for code in codes
    if code not in PRODUCTION_COMPONENTS
}