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
    "결과",
    "곳",
    "인",
    "해줘",
    "해주세요",
    "주세요",
    "해줄래",
    "페이지",
    "화면",
    "열어줘",
    "열어",
    "열기",
    "이동",
    "찾아줘",
    "가줘",
    "위치",
    "얼마나",
    "얼마",
    "뭐",
    "등급",
    "물류",
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

PRODUCT_SEARCH_TERMS = {
    "cart bp pro": "CART BP PRO",
    "cart bp프로": "CART BP PRO",
    "카트 bp pro": "CART BP PRO",
    "카트 bp프로": "CART BP PRO",
    "cart bp": "CART BP",
    "카트 bp": "CART BP",
    "cart on": "CART ON",
    "카트 온": "CART ON",
    "cart platform": "CART PLATFORM",
    "카트 플랫폼": "CART PLATFORM",
    "cart ring": "CART RING",
    "카트 링": "CART RING",
    "cart o2": "CART O2",
    "카트 o2": "CART O2",
}


PAGE_KEYWORDS = [
    (("mrp result", "mrp 결과", "mrp result", "소요량 결과"), "mrp_result"),
    (("bom", "자재명세", "부품 구성"), "bom"),
    (("생산계획", "생산 계획", "production plan"), "production_plan"),
    (("자재 기준", "material master", "업체", "리드타임", "moq"), "material_master"),
    (("품목 관리", "item master"), "item_master"),
    (("활동 로그", "로그"), "activity"),
    (("계정", "사용자", "유저"), "users"),
    (("가계상 재고 입출고",), "stock_history"),
    (("가계상 재고 dashboard", "가계상 재고 대시보드"), "stock_dashboard"),
    (("수불 재고 입출고", "수불재고 입출고", "계상 재고 입출고", "계상재고 입출고"), "inventory_history"),
    (("수불 재고 dashboard", "수불 재고 대시보드", "수불재고 대시보드",
      "계상 재고 dashboard", "계상 재고 대시보드", "계상재고 대시보드"), "inventory_dashboard"),
    (("재고 입출고", "stock history"), "stock_history"),
    (("재고 dashboard", "재고 대시보드"), "stock_dashboard"),
    (("가계상 재고", "book stock", "stock"), "stock"),
    (("수불 재고", "수불재고", "계상 재고", "계상재고", "창고재고", "제공재고", "외주재고"), "inventory"),
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
    (("창고", "warehouse", "mrp 재고", "보유재고", "수불 재고", "수불재고", "계상 재고", "계상재고"), "inventory.search"),
    (("재고", "stock", "가계상", "반제품", "원자재", "제품"), "stock.summary"),
    (("요약", "전체", "현황", "통계"), "system.summary"),
]


def normalize(text):
    return (text or "").strip().lower()


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def wants_move(text):
    return contains_any(
        text,
        (
            "이동", "열어", "열기", "페이지", "화면", "가줘", "찾아줘",
            "있는 곳", "어디있", "어디에 있", "어디야", "어딨",
        )
    )


STRONG_MEANING_WORDS = ("의미", "뜻", "설명", "개념")
WEAK_MEANING_WORDS = ("뭐야", "무엇")
MEANING_WORDS = STRONG_MEANING_WORDS + WEAK_MEANING_WORDS

PARTICLE_PATTERN = re.compile(
    r"\b(그럼|그|이|가|은|는|을|를|의|에서|에|랑|과|와|이랑|으로|로)\b"
)


def wants_meaning(text):
    return contains_any(text, MEANING_WORDS)


def has_specific_target(text, matched_keywords):
    """True if there is more to the question than the matched domain
    keyword(s) and the meaning-question wording itself.

    "BOM이 뭐야" has nothing left over after removing "BOM" and "뭐야" -
    it's asking what the term means. "카트 BP pro 구성품 뭐야" still has
    "카트 BP pro" left over after the same removal - it's a data lookup
    for that specific product; "뭐야" here is just casual phrasing for
    "what is". This is what lets the same "뭐야" ending route to two
    different tools depending on whether a real item/product is named.
    """

    remainder = text

    for keyword in matched_keywords:
        remainder = re.sub(re.escape(keyword), " ", remainder, flags=re.IGNORECASE)

    for word in MEANING_WORDS:
        remainder = re.sub(re.escape(word), " ", remainder, flags=re.IGNORECASE)

    remainder = re.sub(r"[?.,!]", " ", remainder)
    remainder = PARTICLE_PATTERN.sub(" ", remainder)

    return bool("".join(remainder.split()))


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


def translate_product_terms(text):
    """Rewrite Korean/mixed product aliases to the uppercase English
    form the database stores, e.g. "카트 bp pro" -> "CART BP PRO".

    Used for any "item" search string headed for a text LIKE query
    (BOM, stock, material/item master) - regardless of whether that
    string came from the keyword router or the AI planner.
    """

    if not text:
        return text

    result = text

    for alias, search_term in PRODUCT_SEARCH_TERMS.items():
        result = re.sub(re.escape(alias), search_term, result, flags=re.IGNORECASE)

    return " ".join(result.split())


def page_uses_target(page):
    return page not in {
        "dashboard",
        "stock_dashboard",
        "inventory_dashboard",
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

    # "입출고" contains "출고" as a substring, so it must be checked
    # first - otherwise "입출고 알려줘" (both directions) would wrongly
    # resolve to "outbound" only.
    if "입출고" in lowered:
        return "both"

    if "출고" in lowered or "outbound" in lowered:
        return "outbound"

    if "입고" in lowered or "inbound" in lowered:
        return "inbound"

    return "both"


def extract_movement_type(text):
    """Same substring trap as extract_flow_type, but for the IN/OUT
    values InventoryMovement/StockMovement store (vs "inbound"/
    "outbound" for the Inbound/Outbound tables)."""

    lowered = normalize(text)

    if "입출고" in lowered:
        return ""

    if "출고" in lowered:
        return "OUT"

    if "입고" in lowered:
        return "IN"

    return ""


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

    if any(word in lowered for word in ("적은", "최소")):
        return "qty", "asc"

    if any(word in lowered for word in ("많은", "최대", "top")):
        return "qty", "desc"

    return "", "asc"


def extract_page(text):
    lowered = normalize(text)

    for keywords, page in PAGE_KEYWORDS:
        if contains_any(lowered, keywords):
            return page

    return ""


def extract_number(text):
    """First plain number in the text ("215개인" -> "215").

    Used for MRP Result navigation by value ("부족 수량이 215개인 행")
    - extract_keyword's generic cleanup is built for item codes/names
    and reliably leaves stray words (부족/mrp/등) around a bare number,
    which then fails to match anything via the highlight substring
    search.
    """

    match = re.search(r"\d[\d,]*", text or "")
    return match.group(0).replace(",", "") if match else ""


# Routing keywords are normally just phrasing, not real filter values,
# so extract_keyword() strips them before hunting for a literal code.
# "admin" is the exception - it's also this app's actual admin
# username, so "admin 로그인 이력" should still be able to search by it
# instead of losing it to the same stripping that "관리자"/"사용자" get.
CODE_SEARCH_EXCEPTIONS = {"admin"}


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
            if keyword in CODE_SEARCH_EXCEPTIONS:
                continue
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

    # 실제 품목코드/품명 토큰은 항상 숫자를 포함한다(SL-H-AS-00010,
    # Ring_size_7 등). 이 조건이 없으면 "CART-I Ring_size_7"처럼 코드
    # 형태로 시작하는 다단어 품명에서 앞쪽 "CART-I"만 잡고 뒤에 붙은
    # 진짜 식별자("Ring_size_7")를 놓치는 문제가 있었다.
    code = [
        c for c in re.findall(r"\b[A-Za-z0-9][A-Za-z0-9_\-./]{2,}\b", code_source)
        if re.search(r"\d", c)
    ]
    if code:
        return code[0].strip()

    cleaned = re.sub(r"[?.,!<>()]", " ", translate_product_terms(text))

    for word in sorted(STOPWORDS, key=len, reverse=True):
        cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)

    for word in MEANING_WORDS:
        cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)

    for keywords, _ in PAGE_KEYWORDS + DOMAIN_KEYWORDS:
        for keyword in keywords:
            cleaned = re.sub(re.escape(keyword), " ", cleaned, flags=re.IGNORECASE)

    cleaned = PARTICLE_PATTERN.sub(" ", cleaned)

    compact = " ".join(cleaned.split())

    return compact[:80]


def resolve_tool(question):
    text = normalize(question)

    if "mrp" in text and "부족" in text:

        # "top5"/"부족 5개"/"부족 목록" 같은 여러 건 요청은 shortage_max/
        # min(단일 항목, 화면 이동)이 아니라 shortage_search(목록 조회)로
        # 보낸다.
        number = extract_number(question)

        if number and contains_any(text, ("top", "개", "목록", "리스트")):
            return {
                "tool": "mrp.shortage_search",
                "arguments": {
                    "sort": "desc",
                    "limit": int(number.replace(",", "")),
                }
            }

        if contains_any(text, ("적은", "최소", "없는", "낮은")):
            return {
                "tool": "mrp.shortage_min",
                "arguments": {}
            }

        if contains_any(text, ("가장", "제일", "최대", "많은", "높은")):
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

        if page and target and " " in target.strip():
            number = extract_number(question)
            if number:
                target = number

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

    if contains_any(text, ("활동 로그", "활동로그", "작업 이력", "작업이력", "활동 이력")):
        return {
            "tool": "activity.search",
            "arguments": {
                "item": extract_keyword(question)
            }
        }

    # 대시보드 요약 조회 - "열어줘"/"이동" 같은 wants_move 표현이 없을 때만
    # 여기 도달한다(있으면 위 page.move/page.find가 이미 처리함).
    if contains_any(text, ("대시보드", "dashboard")):

        if "가계상" in text:
            return {
                "tool": "stock.dashboard",
                "arguments": {}
            }

        if contains_any(
            text,
            ("수불 재고", "수불재고", "계상 재고", "계상재고", "창고재고", "제공재고", "외주재고")
        ):
            return {
                "tool": "inventory.dashboard",
                "arguments": {}
            }

        if "mrp" in text:
            return {
                "tool": "mrp.dashboard",
                "arguments": {}
            }

        if contains_any(text, ("입고", "출고", "제품 물류", "물류")):
            return {
                "tool": "logistics.dashboard",
                "arguments": {
                    "period": extract_period(question)
                }
            }

    # 재고 입출고 "이력/내역" 조회 - "입출고"는 "출고"를 부분 문자열로
    # 포함하므로, 아래 flow_count 분기보다 먼저 확인해야 한다.
    if contains_any(text, ("이력", "내역")):

        if "가계상" in text:
            return {
                "tool": "stock.movement_search",
                "arguments": {
                    "item": extract_keyword(question),
                    "movement_type": extract_movement_type(text),
                    "period": extract_period(question),
                }
            }

        if contains_any(
            text,
            ("수불 재고", "수불재고", "계상 재고", "계상재고", "창고재고", "제공재고", "외주재고")
        ):
            warehouse_type = ""
            for wt in ("창고재고", "제공재고", "외주재고"):
                if wt in text:
                    warehouse_type = wt
                    break

            return {
                "tool": "inventory.movement_search",
                "arguments": {
                    "item": extract_keyword(question),
                    "warehouse_type": warehouse_type,
                    "movement_type": extract_movement_type(text),
                    "period": extract_period(question),
                }
            }

    def _meaning_or(matched_keywords, data_result):
        if wants_meaning(text) and not has_specific_target(text, matched_keywords):
            return {
                "tool": "knowledge.answer",
                "arguments": {
                    "question": question,
                    "topic": extract_keyword(question),
                }
            }

        return data_result

    if contains_any(text, ("입고", "출고", "inbound", "outbound")):
        matched = [kw for kw in ("입고", "출고", "inbound", "outbound") if kw in text]

        # product가 잡히면 그걸로 이미 충분히 특정된 것이라 keyword를
        # 같이 넘기면 안 된다 - extract_keyword()는 "cart bp pro"처럼
        # 사람이 읽는 형태를 돌려주는데, DB의 product 컬럼은
        # "cart_bp_pro"(언더스코어)로 저장돼 있어서 이 keyword가 별도
        # LIKE 필터로 함께 걸리면 실제로는 매칭될 수 없는 조건이
        # AND로 붙어 항상 0건이 되는 버그가 있었다.
        product = extract_product(question)

        return _meaning_or(matched, {
            "tool": "logistics.flow_count",
            "arguments": {
                "flow_type": extract_flow_type(question),
                "product": product,
                "period": extract_period(question),
                "keyword": "" if product else extract_keyword(question),
            }
        })

    if text == "재고":

        return {

            "tool":"stock.select",

            "arguments":{}

        }

    if "가계상" not in text and contains_any(
        text,
        ("수불 재고", "수불재고", "계상 재고", "계상재고", "창고재고", "제공재고", "외주재고")
    ):
        matched = [
            kw for kw in ("수불 재고", "수불재고", "계상 재고", "계상재고", "창고재고", "제공재고", "외주재고")
            if kw in text
        ]

        warehouse_type = ""
        for wt in ("창고재고", "제공재고", "외주재고"):
            if wt in text:
                warehouse_type = wt
                break

        grade = ""
        grade_match = re.search(r"\b([ABF])\s*등급|등급\s*([ABF])\b", question or "", re.IGNORECASE)
        if grade_match:
            grade = (grade_match.group(1) or grade_match.group(2)).upper()

        lot = ""
        lot_match = re.search(r"lot\s*([A-Za-z]*\d+)", question or "", re.IGNORECASE)
        if lot_match:
            lot = lot_match.group(1)

        scrubbed = re.sub(
            r"(?i)[ABF]\s*등급|등급\s*[ABF]|lot\s*[A-Za-z]*\d*",
            " ",
            question or ""
        )

        return _meaning_or(matched, {
            "tool": "inventory.search",
            "arguments": {
                "item": extract_keyword(scrubbed),
                "warehouse_type": warehouse_type,
                "category": extract_stock_category(question),
                "grade": grade,
                "lot": lot,
            }
        })

    if contains_any(text, ("가계상", "반제품", "원자재", "제품", "재고")):
        matched = [
            kw for kw in ("가계상", "반제품", "원자재", "제품", "재고")
            if kw in text
        ]
        sort, order = extract_sort(question)

        item = "" if sort else extract_keyword(question)

        return _meaning_or(matched, {
            "tool": "stock.summary",
            "arguments": {
                "category": extract_stock_category(question),
                "item": item,
                "sort": sort,
                "order": order,
                "limit": 1 if sort else 15,
            }
        })

    for keywords, tool in DOMAIN_KEYWORDS:
        if contains_any(text, keywords):
            matched = [kw for kw in keywords if kw in text]

            return _meaning_or(matched, {
                "tool": tool,
                "arguments": {
                    "item": extract_keyword(question)
                }
            })

    if wants_meaning(text):
        return {
            "tool": "knowledge.answer",
            "arguments": {
                "question": question,
                "topic": extract_keyword(question),
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