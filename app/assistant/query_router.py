import re


STOPWORDS = {
    "알려줘",
    "보여줘",
    "조회",
    "검색",
    "현황",
    "목록",
    "정보",
    "몇개",
    "몇",
    "개",
    "개수",
    "건",
    "건수",
    "수량",
    "있어",
    "있는지",
    "대해서",
    "데이터",
    "총",
    "전체",
    "오늘",
    "어제",
    "이번주",
    "이번 주",
    "이번달",
    "이번 달",
    "입고",
    "출고",
    "입출고",
    "로그인",
    "이력",
    "한",
    "된",
    "거",
    "야",
    "이야",
    "계정",
    "사용자",
    "유저",
    "품목",
    "코드",
    "가장",
    "최대",
    "최소",
    "많은",
    "적은",
    "순",
    "top",
    "행",
}


PRODUCT_ALIASES = {
    "cart bp pro": "cart_bp_pro",
    "cart bp프로": "cart_bp_pro",
    "카트 bp pro": "cart_bp_pro",
    "카트 bp프로": "cart_bp_pro",
    "cart bp": "cart_bp",
    "카트 bp": "cart_bp",
    "cart on": "cart_on",
    "카트 온": "cart_on",
    "cart platform": "cart_platform",
    "카트 플랫폼": "cart_platform",
    "cart ring": "cart_ring",
    "카트 링": "cart_ring",
    "cart o2": "cart_o2",
    "카트 o2": "cart_o2",
    "한방": "hanbang",
}


PAGE_KEYWORDS = [
    (("mrp result", "mrp 결과", "mrp result", "소요량 결과"), "mrp_result"),
    (("bom", "자재명세", "부품 구성"), "bom"),
    (("생산계획", "생산 계획", "production plan"), "production_plan"),
    (("자재 기준", "material master", "업체", "리드타임", "moq"), "material_master"),
    (("품목 관리", "item master"), "item_master"),
    (("활동 로그", "로그"), "activity"),
    (("계정", "사용자", "유저"), "users"),
    (("재고 입출고", "stock history"), "stock_history"),
    (("재고 dashboard", "재고 대시보드"), "stock_dashboard"),
    (("가계상 재고", "가공상 재고", "book stock", "stock"), "stock"),
    (("mrp",), "mrp"),
    (("dashboard", "대시보드"), "dashboard"),
    (("전체 조회", "통합 조회"), "search"),
]


DOMAIN_KEYWORDS = [
    (("bom", "자재명세", "부품", "구성품", "소요량"), "bom.detail"),
    (("생산계획", "생산 계획", "계획수량", "plan"), "production.plan"),
    (("자재 기준", "material", "업체", "공급사", "리드타임", "lead", "moq"), "material.master"),
    (("품목", "item master", "rev", "리비전"), "item.master"),
    (("이동", "serial", "시리얼"), "movement.search"),
    (("사용자", "유저", "계정", "admin", "관리자"), "admin.user_summary"),
    (("창고", "warehouse", "mrp 재고", "보유재고"), "inventory.search"),
    (("재고", "stock", "가계상", "가공상", "반제품", "원자재", "제품"), "stock.summary"),
    (("요약", "전체", "현황", "통계"), "system.summary"),
]


def normalize(text):
    return (text or "").strip().lower()


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def wants_move(text):
    return contains_any(
        text,
        ("이동", "열어", "열기", "페이지", "화면", "가줘", "찾아줘", "있는 곳")
    )


def wants_meaning(text):
    return contains_any(
        text,
        ("의미", "뜻", "뭐야", "무엇", "설명", "개념")
    )


def is_secret_question(text):
    return contains_any(
        text,
        ("비밀번호", "패스워드", "password", "pw", "암호")
    )


def wants_account_creation(text):
    return contains_any(text, ("생성", "추가", "만들어")) and contains_any(
        text,
        ("계정", "사용자", "유저", "user")
    )


def is_out_of_scope(text):
    return contains_any(
        text,
        ("날씨", "환율", "주가", "뉴스", "날짜", "시간")
    )


def page_uses_target(page):
    return page not in {
        "dashboard",
        "stock_dashboard",
        "mrp",
    }


def extract_product(text):
    lowered = normalize(text)

    for alias, product in PRODUCT_ALIASES.items():
        if alias in lowered:
            return product

    return ""


def extract_period(text):
    lowered = normalize(text)

    if "오늘" in lowered:
        return "today"

    if "어제" in lowered:
        return "yesterday"

    if "이번주" in lowered or "이번 주" in lowered:
        return "this_week"

    if "이번달" in lowered or "이번 달" in lowered:
        return "this_month"

    return "all"


def extract_flow_type(text):
    lowered = normalize(text)

    if "출고" in lowered or "outbound" in lowered:
        return "outbound"

    if "입고" in lowered or "inbound" in lowered:
        return "inbound"

    return "both"


def extract_stock_category(text):
    lowered = normalize(text)

    if "반제품" in lowered:
        return "반제품"

    if "원자재" in lowered:
        return "원자재"

    if "제품" in lowered:
        return "제품"

    return ""

def extract_sort(text):
    lowered = normalize(text)

    if any(word in lowered for word in (
        "가장 많은",
        "제일 많은",
        "최대",
        "top",
        "많은 순",
    )):
        return "qty", "desc"

    if any(word in lowered for word in (
        "가장 적은",
        "최소",
        "적은 순",
    )):
        return "qty", "asc"

    return "", "asc"


def extract_page(text):
    lowered = normalize(text)

    for keywords, page in PAGE_KEYWORDS:
        if contains_any(lowered, keywords):
            return page

    return ""


def extract_keyword(question):
    text = question or ""

    quoted = re.findall(r"['\"]([^'\"]+)['\"]", text)
    if quoted:
        return quoted[0].strip()

    alias_removed = text
    for alias in PRODUCT_ALIASES:
        alias_removed = re.sub(
            re.escape(alias),
            " ",
            alias_removed,
            flags=re.IGNORECASE
        )

    code_source = alias_removed
    for keywords, _ in PAGE_KEYWORDS + DOMAIN_KEYWORDS:
        for keyword in keywords:
            code_source = re.sub(
                re.escape(keyword),
                " ",
                code_source,
                flags=re.IGNORECASE
            )

    code_source = re.sub(
        r"(결과|에서|있는|곳|으로|이동|찾아줘|가줘|가장|최대|최소|많은|적은|순|top|품목|코드|행)",
        " ",
        code_source,
        flags=re.IGNORECASE
    )

    code = re.findall(r"\b[A-Za-z0-9][A-Za-z0-9_\-./]{2,}\b", code_source)
    if code:
        return code[0].strip()

    cleaned = re.sub(r"[?.,!<>()]", " ", alias_removed)

    for word in sorted(STOPWORDS, key=len, reverse=True):
        cleaned = cleaned.replace(word, " ")

    for keywords, _ in PAGE_KEYWORDS + DOMAIN_KEYWORDS:
        for keyword in keywords:
            cleaned = cleaned.replace(keyword, " ")

    compact = " ".join(cleaned.split())

    return compact[:80]


def resolve_tool(question):
    text = normalize(question)

    if (
        "mrp" in text
        and "부족" in text
        and ("가장" in text or "최대" in text)
    ):
        return {
            "tool": "mrp.shortage_max",
            "arguments": {}
        }

    if is_secret_question(text):
        return {
            "tool": "security.block",
            "arguments": {
                "question": question
            }
        }

    if is_out_of_scope(text):
        return {
            "tool": "knowledge.out_of_scope",
            "arguments": {
                "question": question
            }
        }

    if wants_account_creation(text):
        return {
            "tool": "admin.account_action",
            "arguments": {
                "action": "create_user"
            }
        }

    if "로그인" in text:
        return {
            "tool": "activity.login_summary",
            "arguments": {
                "period": extract_period(question),
                "keyword": extract_keyword(question),
            }
        }

    if wants_move(text):
        page = extract_page(question)
        target = extract_keyword(question)

        if target and page_uses_target(page):
            return {
                "tool": "page.find",
                "arguments": {
                    "page": page,
                    "target": target,
                }
            }

        if page:
            return {
                "tool": "page.move",
                "arguments": {
                    "page": page
                }
            }

    if wants_meaning(text):
        return {
            "tool": "knowledge.answer",
            "arguments": {
                "question": question,
                "topic": extract_keyword(question),
            }
        }

    if contains_any(text, ("입고", "출고", "inbound", "outbound")):
        return {
            "tool": "logistics.flow_count",
            "arguments": {
                "flow_type": extract_flow_type(question),
                "product": extract_product(question),
                "period": extract_period(question),
                "keyword": extract_keyword(question),
            }
        }
    
    if text == "재고":

        return {

            "tool":"stock.select",

            "arguments":{}

        }

    if contains_any(text, ("가계상", "가공상", "반제품", "원자재", "제품", "재고")):
        sort, order = extract_sort(question)

        item = "" if sort else extract_keyword(question)

        return {
            "tool": "stock.summary",
            "arguments": {
                "category": extract_stock_category(question),
                "item": item,
                "sort": sort,
                "order": order,
                "limit": 1 if sort else 15,
            }
        }

    for keywords, tool in DOMAIN_KEYWORDS:
        if contains_any(text, keywords):
            return {
                "tool": tool,
                "arguments": {
                    "item": extract_keyword(question)
                }
            }

    keyword = extract_keyword(question)

    if keyword:
        return {
            "tool": "global.search",
            "arguments": {
                "item": keyword
            }
        }

    return {
        "tool": "general.chat",
        "arguments": {
            "question": question
        }
    }