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


# ------------------------------------------------------------------
# 품목 레벨 변환 규칙 (사이즈 8~13)
#
#   level 3 (원자재: INNER / PBA / TOP COVER / OUTER)
#     --생산 완료-->  level 2 (CART_Ring_Rev.2D_size N)
#   level 2 (RING / CRADLE)
#     --포장 완료-->  level 1 (CART PLATFORM IEM_size N)
#
# 품목코드/품명은 아래 맵으로 자동 변경되고, LOT는 생산/포장을
# 수행한 생산팀이 직접 입력한다. 맵에 없는 품목은 변환 없이
# 코드/품명을 유지한 채 진행된다.
# ------------------------------------------------------------------

def _build_level_transforms():
    production = {}             # level3 code -> (level2 code, level2 name)
    packaging = {}              # level2 code -> (level1 code, level1 name)
    production_components = {}  # level2 code -> [필요한 level3 코드 4종]
    packaging_components = {}   # level1 code -> [필요한 level2 코드 2종]

    for i, size in enumerate(range(8, 14)):
        level1_code = f"SL-P-PD-{110 + i:05d}"
        level1_name = f"CART PLATFORM IEM_size {size}"

        cradle_code = f"SL-P-HG-{92 + i:05d}"
        ring_code = f"SL-P-HG-{148 + i:05d}"
        ring_name = f"CART_Ring_Rev.2D_size {size}"

        level3_codes = [
            f"SL-M-RM-{199 + i:05d}",   # Ring_INNER_PC_MRA2K
            f"SL-H-AS-{87 + i:05d}",    # ASS'Y_RING_PBA_V3.3.2 Discrete
            f"SL-M-RM-{286 + i:05d}",   # RING_TOP COVER_V2
            f"SL-M-RM-{339 + i:05d}",   # Ring_OUTER_V1
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

# 포장 구성품 중 "이미 반제품으로 구매되는" 품목(CRADLE) - RING처럼
# 원자재 4종을 조립해 생산팀이 만들어내는 게 아니라 애초에 완제된
# 반제품 형태로 입고된다. 그래서 원자재와 달리 생산(조립)·공정검사
# 단계가 필요 없고, 품질 입고검사 이후 자재 확인만 거치면 곧바로
# 포장 요청으로 넘어가야 한다.
PREMADE_PACKAGING_CODES = {
    code
    for codes in PACKAGING_COMPONENTS.values()
    for code in codes
    if code not in PRODUCTION_COMPONENTS
}