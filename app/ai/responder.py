import json

from app.ai.client import ask_ai
from app.ai.prompts import ANSWER_PROMPT, GENERAL_KNOWLEDGE_PROMPT


PERIOD_LABELS = {
    "today": "오늘",
    "yesterday": "어제",
    "this_week": "이번 주",
    "this_month": "이번 달",
    "all": "전체 기간",
}


def _garbled(text):
    """Groq가 간혹 U+FFFD(�) 범벅인 깨진 텍스트를 반환한다 - 그대로
    사용자에게 보여주는 대신 결정적 fallback 답변으로 대체한다."""
    return bool(text) and text.count("�") >= 3


def make_answer(question, result):
    if result.get("type") == "move":
        return result.get("message", "요청한 화면으로 이동합니다.")

    fallback = _fallback_answer(result)

    if result.get("status") == "blocked":
        return fallback

    if result.get("status") == "general":
        ai_answer = ask_ai(
            user_message=question,
            system_prompt=GENERAL_KNOWLEDGE_PROMPT,
        )

        if _garbled(ai_answer):
            return fallback

        return ai_answer or fallback

    AI_REQUIRED = {
        "rows",
        "global_search",
        "summary",
        "stock_summary",
        "flow_count",
        "users",
        "login_summary",
        "logistics_dashboard",
        "inventory_dashboard",
        "stock_dashboard",
        "mrp_dashboard",
    }

    if result.get("status") not in AI_REQUIRED:
        return fallback

    context = json.dumps(
        {
            "question": question,
            "result": result
        },
        ensure_ascii=False,
        default=str
    )

    ai_answer = ask_ai(
        user_message=context,
        system_prompt=ANSWER_PROMPT
    )

    if _garbled(ai_answer):
        return fallback

    return ai_answer or fallback


def _fallback_answer(result):
    status = result.get("status")

    if status == "blocked":
        return result.get("message", "보안상 해당 정보는 제공할 수 없습니다.")

    if status == "out_of_scope":
        return result.get("message", "Logistics 시스템 범위 밖의 질문입니다.")

    if status == "flow_count":
        return _flow_count_answer(result)

    if status == "stock_summary":
        return _stock_summary_answer(result)

    if status == "login_summary":
        return _login_summary_answer(result)

    if status == "logistics_dashboard":
        return _logistics_dashboard_answer(result)

    if status == "inventory_dashboard":
        return _inventory_dashboard_answer(result)

    if status == "stock_dashboard":
        return _stock_dashboard_answer(result)

    if status == "mrp_dashboard":
        return _mrp_dashboard_answer(result)

    if status == "none":
        return result.get("message", "조회된 데이터가 없습니다.")

    if status == "account_action":
        return result.get("message", "관리자 화면에서 처리해 주세요.")

    if status == "knowledge":
        return _knowledge_answer(result)
    
    if status=="need_stock_type":

        return (
            "어떤 재고를 조회하시겠습니까?\n\n"
            "• 가계상 재고\n"
            "• 수불 재고"
        )

    if status == "need_page_choice":
        target = result.get("target", "")
        choices = result.get("choices", [])

        lines = [
            f"'{target}'이(가) 여러 화면에 있습니다. 어디로 이동할까요?",
            "",
        ]
        lines.extend(
            f"{i}. {choice.get('label', '')}"
            for i, choice in enumerate(choices, 1)
        )
        lines.append("")
        lines.append("번호나 이름으로 답해 주세요.")

        return "\n".join(lines)

    if status == "summary":
        counts = result.get("counts", {})
        return (
            "현재 Logistics 시스템 요약입니다.\n\n"
            f"- 제품 물류 입고: {counts.get('inbound', 0):,}건\n"
            f"- 제품 물류 출고: {counts.get('outbound', 0):,}건\n"
            f"- 시리얼 이동 이력: {counts.get('movements', 0):,}건\n"
            f"- 가계상 재고 수량: {counts.get('book_stock_qty', 0):,} EA\n"
            f"- 수불 재고 수량: {counts.get('inventory_qty', 0):,} EA\n"
            f"- BOM: {counts.get('bom_rows', 0):,}건\n"
            f"- 생산계획 수량: {counts.get('production_plan_qty', 0):,} EA\n"
            f"- 사용자: {counts.get('users', 0):,}명"
        )

    if status == "users":
        role_counts = result.get("role_counts", {})
        rows = result.get("rows", [])
        lines = [
            "사용자 계정 요약입니다.",
            "",
            f"- 관리자: {role_counts.get('admin', 0):,}명",
            f"- 일반 사용자: {role_counts.get('user', 0):,}명",
            f"- 비밀번호 변경 필요: {result.get('must_change_password_count', 0):,}명",
        ]

        if rows:
            lines.append("")
            lines.append("조회된 계정:")
            lines.extend(
                f"- {row['username']} ({row['role']})"
                for row in rows
            )

        return "\n".join(lines)

    if status == "global_search":
        keyword = result.get("keyword", "")
        sections = []

        for key, label in [
            ("book_stock", "가계상 재고"),
            ("inventory", "수불 재고"),
            ("bom", "BOM"),
            ("production_plan", "생산계획"),
            ("material_master", "자재 기준정보"),
            ("item_master", "품목 기준정보"),
        ]:
            rows = result.get(key, [])
            if rows:
                sections.append(f"- {label}: {len(rows)}건")

        if not sections:
            return f"'{keyword}'에 대한 데이터를 찾지 못했습니다."

        return f"'{keyword}' 검색 결과입니다.\n\n" + "\n".join(sections)

    if status == "rows":
        rows = result.get("rows", [])

        if isinstance(rows, dict):
            return _movement_answer(rows)

        if not rows:
            keyword = result.get("keyword")
            if keyword:
                return f"'{keyword}'에 대한 데이터를 찾지 못했습니다."
            return "조회된 데이터가 없습니다."

        return _rows_answer(result)

    if status == "general":
        return result.get("message", "질문을 조금 더 구체적으로 입력해 주세요.")

    if result.get("success") is False:
        return result.get("message", "요청을 처리할 수 없습니다.")

    return "요청을 처리했습니다."


def _flow_count_answer(result):
    product_name = result.get("product_name") or "전체 제품"
    period = PERIOD_LABELS.get(result.get("period"), "전체 기간")
    flow_type = result.get("flow_type")

    if flow_type == "inbound":
        lines = [
            f"{period} {product_name} 입고 데이터는 {result.get('inbound_count', 0):,}건입니다."
        ]
        rows = result.get("inbound_rows", [])
    elif flow_type == "outbound":
        lines = [
            f"{period} {product_name} 출고 데이터는 {result.get('outbound_count', 0):,}건입니다."
        ]
        rows = result.get("outbound_rows", [])
    else:
        lines = [
            f"{period} {product_name} 입출고 데이터입니다.",
            f"- 입고: {result.get('inbound_count', 0):,}건",
            f"- 출고: {result.get('outbound_count', 0):,}건",
        ]
        rows = (result.get("inbound_rows", []) + result.get("outbound_rows", []))[:5]

    if rows:
        lines.append("")
        lines.append("최근 데이터:")
        for row in rows[:5]:
            lines.append(
                f"- {row.get('created_at')} {row.get('product_name') or row.get('product')} "
                f"{row.get('serial') or '-'}"
            )

    return "\n".join(lines)


def _stock_summary_answer(result):
    category = result.get("category")
    keyword = result.get("keyword")

    title = "가계상 재고"
    if category:
        title += f" {category}"
    elif keyword:
        title += f" '{keyword}'"

    lines = [
        f"{title} 조회 결과입니다.",
        f"- 품목 행 수: {result.get('total_rows', 0):,}건",
        f"- 총 수량: {result.get('total_qty', 0):,} EA",
    ]

    if not category and result.get("category_summary"):
        lines.append("")
        lines.append("카테고리별 합계:")
        for row in result["category_summary"]:
            lines.append(
                f"- {row['category']}: {row['row_count']:,}건, {row['qty']:,} EA"
            )

    rows = result.get("rows", [])
    if rows:
        lines.append("")
        lines.append("상위 조회 데이터:")
        for row in rows[:5]:
            lines.append(
                f"- {row['item_name']} ({row['item_code']}), "
                f"{row['category']}, {row['qty']:,} EA"
            )

    if result.get("truncated"):
        lines.append("")
        lines.append("결과가 많아 일부만 표시했습니다. 품목명이나 코드로 더 좁혀 주세요.")

    return "\n".join(lines)


def _login_summary_answer(result):
    period = PERIOD_LABELS.get(result.get("period"), "전체 기간")
    lines = [
        f"{period} 로그인 이력은 {result.get('count', 0):,}건입니다."
    ]

    users = result.get("users", [])
    if users:
        lines.append(f"- 로그인 계정: {', '.join(users)}")

    rows = result.get("rows", [])
    if rows:
        lines.append("")
        lines.append("최근 로그인:")
        for row in rows[:8]:
            lines.append(
                f"- {row.get('created_at')} {row.get('user') or '-'}"
            )

    if result.get("truncated"):
        lines.append("")
        lines.append("이력이 많아 일부만 표시했습니다.")

    return "\n".join(lines)


def _logistics_dashboard_answer(result):
    period = PERIOD_LABELS.get(result.get("period"), "전체 기간")

    return (
        f"제품 물류 현황입니다.\n\n"
        f"- 전체 누적 입고: {result.get('total_in', 0):,}건\n"
        f"- 전체 누적 출고: {result.get('total_out', 0):,}건\n"
        f"- {period} 입고: {result.get('period_in', 0):,}건\n"
        f"- {period} 출고: {result.get('period_out', 0):,}건\n"
        f"- 출고 정보 미입력: {result.get('missing', 0):,}건"
    )


def _inventory_dashboard_answer(result):
    lines = [
        "수불 재고(창고재고) 현황입니다.",
        "",
        f"- 품목 수: {result.get('total_items', 0):,}건",
        f"- 총 수량: {result.get('total_qty', 0):,} EA",
        f"- 입고: {result.get('today_in', 0):,} EA",
        f"- 출고: {result.get('today_out', 0):,} EA",
    ]

    category_summary = result.get("category_summary", [])
    if category_summary:
        lines.append("")
        lines.append("구분별 수량:")
        lines.extend(
            f"- {row['category']}: {row['qty']:,} EA"
            for row in category_summary
        )

    return "\n".join(lines)


def _stock_dashboard_answer(result):
    lines = [
        "가계상 재고 현황입니다.",
        "",
        f"- 품목 수: {result.get('total_items', 0):,}건",
        f"- 총 수량: {result.get('total_qty', 0):,} EA",
        f"- 입고: {result.get('today_in', 0):,} EA",
        f"- 출고: {result.get('today_out', 0):,} EA",
    ]

    category_summary = result.get("category_summary", [])
    if category_summary:
        lines.append("")
        lines.append("카테고리별 수량:")
        lines.extend(
            f"- {row['category']}: {row['qty']:,} EA"
            for row in category_summary
        )

    return "\n".join(lines)


def _mrp_dashboard_answer(result):
    lines = [
        "MRP 대시보드 요약입니다.",
        "",
        f"- 전체 품목: {result.get('total_items', 0):,}건",
        f"- 부족 품목: {result.get('shortage_count', 0):,}건",
        f"- 총 소요량: {result.get('total_required', 0):,}",
        f"- 총 가용재고: {result.get('total_stock', 0):,}",
        f"- 총 부족수량: {result.get('total_shortage', 0):,}",
        f"- 부족률: {result.get('shortage_rate', 0)}%",
    ]

    top_shortages = result.get("top_shortages", [])
    if top_shortages:
        lines.append("")
        lines.append("부족 수량 상위 품목:")
        lines.extend(
            f"- {row['item_name']} ({row['item_code']}): 부족 {row['shortage_qty']:,}"
            for row in top_shortages
        )

    return "\n".join(lines)


def _knowledge_answer(result):
    question = (result.get("question") or "").lower()
    facts = result.get("facts", {})

    for key, value in facts.items():
        if key.lower().replace(" ", "") in question.replace(" ", ""):
            return value

    topic = result.get("topic")
    if topic:
        return (
            f"'{topic}'에 대한 고정 업무 설명은 아직 등록되어 있지 않습니다. "
            "다만 데이터 조회가 필요한 질문이면 시스템 데이터 기준으로 다시 조회해 드릴 수 있습니다."
        )

    return (
        "업무 용어 설명은 DB 조회 없이 답변할 수 있습니다. "
        "예: 가계상 재고, 제품 물류, MRP, BOM의 의미를 물어볼 수 있습니다."
    )


def _rows_answer(result):
    domain = result.get("domain", "data")
    rows = result.get("rows", [])
    label = _domain_label(domain)
    lines = [f"{label} 조회 결과 {len(rows)}건입니다.", ""]

    for index, row in enumerate(rows, 1):
        lines.append(f"{index}. {_format_row(domain, row)}")

    if result.get("truncated"):
        lines.append("")
        lines.append("결과가 많아 일부만 표시했습니다. 품목명이나 코드로 더 좁혀 주세요.")

    return "\n".join(lines)


def _movement_answer(rows):
    serial_rows = rows.get("serial_movements", [])
    stock_rows = rows.get("stock_movements", [])
    lines = [
        f"이동 이력 조회 결과입니다. 시리얼 이력 {len(serial_rows)}건, 재고 이력 {len(stock_rows)}건입니다.",
        ""
    ]

    for row in serial_rows[:5]:
        lines.append(
            f"- {row.get('created_at')} {row.get('product')} "
            f"{row.get('serial')} {row.get('type')} ({row.get('user') or '-'})"
        )

    for row in stock_rows[:5]:
        lines.append(
            f"- {row.get('created_at')} {row.get('item_name')} "
            f"{row.get('movement_type')} {row.get('qty'):,} EA ({row.get('user') or '-'})"
        )

    return "\n".join(lines).strip()


def _domain_label(domain):
    return {
        "book_stock": "가계상 재고",
        "inventory": "수불 재고",
        "bom": "BOM",
        "production_plan": "생산계획",
        "material_master": "자재 기준정보",
        "item_master": "품목 기준정보",
        "item_master_history": "품목 변경 이력",
        "activity": "활동 로그",
        "inventory_movement": "수불 재고 입출고 이력",
        "stock_movement": "가계상 재고 입출고 이력",
        "mrp_result": "MRP 부족 수량",
    }.get(domain, "데이터")


def _format_row(domain, row):
    if domain == "book_stock":
        return (
            f"{row['item_name']} ({row['item_code']}) "
            f"{row['qty']:,} EA, Grade {row.get('grade') or '-'}, Rev {row.get('rev') or '-'}"
        )

    if domain == "inventory":
        extra = ", ".join(
            filter(None, [
                row.get("category"),
                f"LOT {row['lot']}" if row.get("lot") else "",
                f"Grade {row['grade']}" if row.get("grade") else "",
            ])
        )
        return (
            f"{row['item_name']} ({row['item_code']}) "
            f"{row['warehouse_type']}"
            f"{f' [{extra}]' if extra else ''}: {row['qty']:,} EA"
        )

    if domain == "bom":
        return (
            f"{row['product_name']} -> {row['component_name']} "
            f"({row['component_code']}), 소요 {row['qty']}"
        )

    if domain == "production_plan":
        return (
            f"{row['plan_date']} {row['product_name']} "
            f"{row['plan_qty']:,} EA"
        )

    if domain == "material_master":
        return (
            f"{row['item_name']} ({row['item_code']}), "
            f"업체 {row.get('supplier') or '-'}, LT {row.get('lead_time_week', 0)}주, "
            f"MOQ {row.get('moq', 0):,}"
        )

    if domain == "item_master":
        return (
            f"{row['item_name']} ({row['item_code']}), Rev {row.get('rev') or '-'}"
        )

    if domain == "activity":
        return (
            f"{row['created_at']} {row.get('user') or '-'} "
            f"{row.get('action') or '-'} {row.get('product') or ''} {row.get('serial') or ''}".strip()
        )

    if domain in ("inventory_movement", "stock_movement"):
        warehouse = f" {row['warehouse_type']}" if row.get("warehouse_type") else ""
        return (
            f"{row['created_at']} {row['item_name']} ({row['item_code']}){warehouse} "
            f"{row.get('movement_type') or '-'} {row.get('qty', 0):,} EA ({row.get('user') or '-'})"
        )

    if domain == "mrp_result":
        return (
            f"{row['item_name']} ({row['item_code']}) 부족 {row.get('shortage_qty', 0):,}, "
            f"권장발주 {row.get('recommended_order_qty', 0):,}, "
            f"필요일 {row.get('need_date') or '-'}, 업체 {row.get('supplier') or '-'}"
        )

    if domain == "item_master_history":
        return (
            f"{row['created_at']} {row.get('old_code') or '-'}->{row.get('new_code') or '-'} "
            f"({row.get('old_name') or '-'}->{row.get('new_name') or '-'}), "
            f"Rev {row.get('old_rev') or '-'}->{row.get('new_rev') or '-'} ({row.get('user') or '-'})"
        )

    return ", ".join(f"{key}: {value}" for key, value in row.items())
