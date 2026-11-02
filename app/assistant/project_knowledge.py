"""Curated user-facing knowledge derived from the project's upload handlers.

Keep validation facts here so assistant answers are deterministic and do not
depend on an LLM guessing details that are enforced by application code.
"""

UPLOAD_SCHEMAS = (
    {
        "name": "수불 재고",
        "keywords": ("수불", "계상", "inventory"),
        "required": ("품목코드", "창고구분"),
        "optional": ("구분", "LOT", "Grade", "수량", "비고"),
        "note": "창고구분은 창고재고/제공재고/외주재고 중 하나입니다.",
    },
    {
        "name": "원자재 LOT",
        "keywords": ("원자재 lot", "lot 업로드", "lot엑셀"),
        "required": ("품목코드", "Grade", "LOT", "수량"),
        "optional": ("최초 입고일자 또는 입고일자",),
        "note": "품목코드, Grade, LOT 값은 각 데이터 행에서도 비어 있으면 안 됩니다.",
    },
    {
        "name": "가계상 재고",
        "keywords": ("가계상", "장부", "stock"),
        "required": ("품목코드", "구분", "등급", "수량"),
        "optional": (),
        "note": "등록된 품목코드만 반영되고 없는 품목은 제외됩니다.",
    },
    {
        "name": "품목 기준정보",
        "keywords": ("품목 기준", "품목관리", "item master", "itemmaster"),
        "required": ("품목코드", "품명", "Rev"),
        "optional": (),
        "note": "이미 존재하는 품목코드는 신규 등록에서 제외됩니다.",
    },
    {
        "name": "BOM",
        "keywords": ("bom", "자재명세"),
        "required": ("Product", "Item Code", "Item Name", "Qty"),
        "optional": (),
        "note": "한글 별칭 제품명/품목코드/품목명/소요량도 인식합니다.",
    },
    {
        "name": "생산계획",
        "keywords": ("생산계획", "생산 계획"),
        "required": ("6행의 사이즈 열", "6행의 날짜 열"),
        "optional": (),
        "note": "생산계획 전용 양식처럼 6번째 행을 헤더로 사용합니다.",
    },
    {
        "name": "자재 기준정보",
        "keywords": ("자재 기준", "material master", "materialmaster"),
        "required": ("품목코드", "품목명", "업체명", "MOQ", "리드타임"),
        "optional": (),
        "note": "리드타임은 LT(주), LT, L/T, L/Time, 리드타임, Lead Time 중 하나를 사용할 수 있습니다.",
    },
    {
        "name": "제품 물류 입출고",
        "keywords": ("제품 물류", "입고 엑셀", "출고 엑셀", "시리얼"),
        "required": ("입고/출고 문구가 포함된 날짜 열", "Serial 열", "Size 또는 호수 열"),
        "optional": ("구분", "출고처"),
        "note": "입고와 출고 모드에 따라 날짜 열 이름이 달라질 수 있습니다.",
    },
    {
        "name": "대여 재고",
        "keywords": ("대여 재고", "대여재고"),
        "required": ("품목코드", "품명", "수량"),
        "optional": (),
        "note": "열 이름의 공백은 무시됩니다.",
    },
    {
        "name": "대여 입출고 이력",
        "keywords": ("대여 이력", "대여입출고", "대여 입출고"),
        "required": (
            "이력ID", "구분", "분류", "품목코드", "품명", "수량", "본부",
            "부서", "요청자", "사이즈", "S/N", "불출일자", "비고",
        ),
        "optional": (),
        "note": "신규 행은 분류·품목코드·요청자·S/N 등 필수 값도 채워야 합니다.",
    },
    {
        "name": "구매 Workflow",
        "keywords": ("구매", "workflow", "워크플로우"),
        "required": ("Product", "품목코드", "품명", "LOT", "입고 수량", "입고 일자"),
        "optional": (),
        "note": "빈 행은 건너뛰지만 데이터가 있는 행의 필수 값은 모두 입력해야 합니다.",
    },
)


def find_upload_schema(question):
    normalized = " ".join((question or "").lower().split())
    matches = []
    for schema in UPLOAD_SCHEMAS:
        score = max((len(keyword) for keyword in schema["keywords"] if keyword in normalized), default=0)
        if score:
            matches.append((score, schema))
    if not matches:
        return None
    matches.sort(key=lambda pair: pair[0], reverse=True)
    return matches[0][1]


def format_upload_help(question):
    schema = find_upload_schema(question)
    if schema is None:
        names = ", ".join(item["name"] for item in UPLOAD_SCHEMAS)
        return (
            "어떤 엑셀 업로드인지 알려주세요. 현재 안내 가능한 종류는 "
            f"{names}입니다. 예: ‘수불 재고 엑셀 필수 열 알려줘’"
        )

    required = ", ".join(schema["required"])
    lines = [f"{schema['name']} 엑셀 업로드의 필수 열은 {required}입니다."]
    if schema["optional"]:
        lines.append(f"선택 열은 {', '.join(schema['optional'])}입니다.")
    if schema["note"]:
        lines.append(schema["note"])
    return "\n".join(lines)
