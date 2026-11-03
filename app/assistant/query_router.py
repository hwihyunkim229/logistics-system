import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TYPO_ALIASES = {
    "수불제고": "수불재고",
    "가계상제고": "가계상재고",
    "창고제고": "창고재고",
    "외주제고": "외주재고",
    "제공제고": "제공재고",
    "생산게획": "생산계획",
    "워크플로": "워크플로우",
    "mpt": "mrp",
    "mrt": "mrp",
    "부족자제": "부족자재",
    "부족 자제": "부족 자재",
    "생상계획": "생산계획",
    "생산개획": "생산계획",
    "워크플로어": "워크플로우",
    "워크플로으": "워크플로우",
    "플렛폼": "플랫폼",
    "플래폼": "플랫폼",
    "입출고현항": "입출고현황",
    "재고현항": "재고현황",
    "업로두": "업로드",
}

def correct_common_typos(text):
    corrected = text or ""
    for typo, value in sorted(TYPO_ALIASES.items(), key=lambda pair: len(pair[0]), reverse=True):
        if typo == "워크플로":
            corrected = re.sub(r"워크플로(?!우)", value, corrected)
        else:
            corrected = corrected.replace(typo, value)
    return corrected

STOPWORDS = {
    "알려줘",
    "보여줘",
    "조회",
    "검색",
    "현황",
    "목록",
    "내역",
    "기록",
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
    "있는",
    "어떤",
    "말고",
    "확인",
    "확인해줘",
    "확인해주세요",
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
    (("workflow 구매", "워크플로우 구매"), "workflow_purchase"),
    (("workflow 품질", "워크플로우 품질"), "workflow_quality"),
    (("workflow 자재", "워크플로우 자재"), "workflow_material"),
    (("workflow 생산", "워크플로우 생산"), "workflow_production"),
    (("workflow dashboard", "워크플로우 대시보드"), "workflow_dashboard"),
    (("대여 입출고", "대여 이력"), "rental_history"),
    (("대여 재고", "대여재고"), "rental"),
    (("mrp result", "mrp 결과", "mrp result", "소요량 결과"), "mrp_result"),
    (("result", "결과 화면", "결과 페이지", "결과로"), "mrp_result"),
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
    value = (text or "").strip().lower()
    value = re.sub(r"[~ㅋㅎㅠㅜ!?.,]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return correct_common_typos(value)

def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)

def wants_move(text):
    return contains_any(
        text,
        (
            "이동", "열어", "열기", "페이지", "화면", "가줘",
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

def asks_capabilities(text):
    compact = "".join((text or "").split())
    return any(
        phrase in compact
        for phrase in (
            "뭘할수있", "뭐할수있", "무엇을할수있", "어떤걸할수있",
            "어떤질문", "사용법", "도움말", "기능알려", "뭐하는애",
            "뭐하는거", "무슨일해", "너는누구", "넌누구", "정체가뭐",
            "역할이뭐", "어떤도우미", "너뭐야", "넌뭐야",
            "어떤업무도와", "무슨업무도와", "뭘도와", "도와줄수있",
        )
    )

def looks_like_conversation(text):
    compact = "".join((text or "").split())
    return any(
        marker in compact
        for marker in (
            "안녕", "고마워", "감사", "반가워", "잘가", "수고",
            "너", "넌", "assistant", "어시스턴트", "도우미",
        )
    )

def asks_unsupported_analysis(text):
    """Detect questions that require causal or cross-domain computation.

    Sending these to a single lookup tool produces a confident but unrelated
    answer. Until composed queries are implemented, be explicit about the
    limitation and suggest the closest supported questions.
    """
    compact = "".join((text or "").split())
    return any(
        phrase in compact
        for phrase in (
            "왜줄", "왜늘", "원인이뭐", "원인알려",
            "생산가능한수량", "몇개생산가능", "문제될자재",
            "부족자재우선순위", "재고부족한거우선순위",
        )
    )

def asks_upload_help(text):
    return contains_any(
        text,
        ("엑셀", "excel", "업로드", "양식", "필수 열", "필수행", "필수 행", "컬럼"),
    ) or ("파일" in text and contains_any(text, ("열", "필수", "lot")))

def has_inventory_context(text):
    compact = re.sub(r"\s+", "", text or "")
    if any(term in compact for term in ("수불", "수불재고", "계상재고", "창고재고", "제공재고", "외주재고")):
        return True
    if "창고" in compact and any(term in compact for term in ("원자재", "자재", "원료", "반제품", "제품", "수량")):
        return True
    return "재고" in compact and any(term in compact for term in ("창고", "제공", "외주"))

def extract_warehouse_type(text):
    compact = re.sub(r"\s+", "", text or "")
    for marker, value in (("외주", "외주재고"), ("제공", "제공재고"), ("창고", "창고재고")):
        if marker in compact and "재고" in compact:
            return value
    return ""

def translate_product_terms(text):

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

def extract_workflow_item(text):
    value = text or ""
    for alias in PRODUCT_ALIASES:
        value = re.sub(re.escape(alias), " ", value, flags=re.IGNORECASE)
    value = re.sub(
        r"(?i)workflow|워크플로우|번호|부여된|부여|지금|현재|목록|리스트|좀|제발|"
        r"알려줘|알려주세요|알려주라|보여줘|보여주세요|확인해줘|찾아줘|찾기|검색|조회",
        " ",
        value,
    )
    value = re.sub(r"[?.,!]", " ", value)
    value = " ".join(value.split())
    value = re.sub(r"(?:에서|에게|으로|로|에|의|은|는|이|가|을|를)$", "", value)
    return value.strip()

def extract_scoped_keyword(question, scope_words):
    value = question or ""
    for word in scope_words:
        value = re.sub(re.escape(word), " ", value, flags=re.IGNORECASE)
    return extract_keyword(value)

def extract_workflow_department(text):
    for markers, value in (
        (("품질팀", "품질 부서", "품질부서", "quality"), "quality"),
        (("구매팀", "구매 부서", "구매부서", "purchase"), "purchase"),
        (("자재팀", "자재 부서", "자재부서", "material"), "material"),
        (("생산팀", "생산 부서", "생산부서", "production"), "production"),
    ):
        if contains_any(text, markers):
            return value
    return ""

def extract_period(text):
    lowered = normalize(text)
    compact = re.sub(r"\s+", "", lowered)

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()

    iso_range = re.search(
        r"(20\d{2})[-./년](\d{1,2})[-./월](\d{1,2})일?(?:부터|~|에서|-)(20\d{2})[-./년](\d{1,2})[-./월](\d{1,2})일?(?:까지)?",
        compact,
    )
    if iso_range:
        values = [int(value) for value in iso_range.groups()]
        try:
            start = date(values[0], values[1], values[2])
            end = date(values[3], values[4], values[5])
            if start <= end:
                return f"range_{start:%Y%m%d}_{end:%Y%m%d}"
        except ValueError:
            pass

    month_day_range = re.search(
        r"(\d{1,2})월(\d{1,2})일?(?:부터|~|에서|-)(\d{1,2})월(\d{1,2})일?(?:까지)?",
        compact,
    )
    if month_day_range:
        sm, sd, em, ed = (int(value) for value in month_day_range.groups())
        try:
            start = date(today.year, sm, sd)
            end = date(today.year, em, ed)
            if end < start:
                end = date(today.year + 1, em, ed)
            return f"range_{start:%Y%m%d}_{end:%Y%m%d}"
        except ValueError:
            pass

    single_date = re.search(r"(?:(20\d{2})년)?(\d{1,2})월(\d{1,2})일", compact)
    if single_date:
        year, month, day = single_date.groups()
        try:
            target = date(int(year) if year else today.year, int(month), int(day))
            return f"date_{target:%Y%m%d}"
        except ValueError:
            pass

    if "지난달" in compact or "저번달" in compact:
        return "previous_month"

    if "지난주" in compact or "저번주" in compact:
        return "previous_week"

    if "이번주" in compact or "금주" in compact:
        return "this_week"

    if "이번달" in compact or "금월" in compact:
        return "this_month"

    korean_counts = {"한": 1, "일": 1, "두": 2, "이": 2, "세": 3, "삼": 3, "네": 4, "사": 4}
    duration = re.search(
        r"(?:최근|지난)(\d+|한|일|두|이|세|삼|네|사)(일|주|개월|달)",
        compact,
    )
    if duration:
        raw_count, unit = duration.groups()
        count = int(raw_count) if raw_count.isdigit() else korean_counts[raw_count]
        suffix = {"일": "days", "주": "weeks", "개월": "months", "달": "months"}[unit]
        return f"last_{count}_{suffix}"

    duration_without_prefix = re.search(
        r"(\d+|한|일|두|이|세|삼|네|사)(일|주|개월|달)(?:동안|간|치|전부터)",
        compact,
    )
    if duration_without_prefix:
        raw_count, unit = duration_without_prefix.groups()
        count = int(raw_count) if raw_count.isdigit() else korean_counts[raw_count]
        suffix = {"일": "days", "주": "weeks", "개월": "months", "달": "months"}[unit]
        return f"last_{count}_{suffix}"

    if any(phrase in compact for phrase in ("최근일주일", "지난일주일")):
        return "last_1_weeks"

    if "오늘" in lowered:
        return "today"

    if "어제" in lowered:
        return "yesterday"

    if "이번주" in lowered or "이번 주" in lowered:
        return "this_week"

    if "이번달" in lowered or "이번 달" in lowered:
        return "this_month"

    return "all"

def is_rolling_period(period):
    return (period or "").startswith("last_")

def bare_day_count(text):
    compact = re.sub(r"\s+", "", normalize(text))
    if any(marker in compact for marker in ("최근", "지난", "동안", "간", "치", "전부터", "월")):
        return None
    match = re.search(r"(?<!\d)(\d{1,3})일(?!\d)", compact)
    return int(match.group(1)) if match else None

def invalid_explicit_date(text):
    compact = re.sub(r"\s+", "", text or "")
    for year, month, day in re.findall(r"(?:(20\d{2})년)?(\d{1,2})월(\d{1,2})일", compact):
        try:
            date(int(year) if year else datetime.now(ZoneInfo("Asia/Seoul")).year, int(month), int(day))
        except ValueError:
            return f"{year + '년 ' if year else ''}{int(month)}월 {int(day)}일은 유효한 날짜가 아닙니다. 날짜를 다시 확인해 주세요."
    return ""

def extract_flow_type(text):
    lowered = normalize(text)

    if "입출고" in lowered:
        return "both"

    if "출고" in lowered or "outbound" in lowered or "나갔" in lowered or "내보" in lowered:
        return "outbound"

    if "입고" in lowered or "inbound" in lowered or "들어왔" in lowered or "들어온" in lowered:
        return "inbound"

    return "both"

def extract_movement_type(text):

    lowered = normalize(text)

    if "최근" in lowered:
        recent_text = lowered.split("최근", 1)[1]
        if "입고" in recent_text and "출고" not in recent_text:
            return "IN"
        if "출고" in recent_text and "입고" not in recent_text:
            return "OUT"

    if "입출고" in lowered or ("입고" in lowered and "출고" in lowered):
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

    if "원자재" in lowered or "원료" in lowered or "자재" in lowered:
        return "원자재"

    if "제품" in lowered:
        return "제품"

    return ""

def remove_inventory_scope_words(keyword, category=""):
    """Remove generic inventory scope nouns accidentally parsed as item names."""
    value = (keyword or "").strip()
    generic_by_category = {
        "원자재": {"자재", "원료", "원자재"},
        "반제품": {"반제품"},
        "제품": {"제품", "완제품"},
    }
    if value in generic_by_category.get(category, set()):
        return ""
    if value in {"재고", "품목", "물품", "전체", "전부", "창고", "외주", "제공"}:
        return ""
    return value

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
    match = re.search(r"\d[\d,]*", text or "")
    return match.group(0).replace(",", "") if match else ""

CODE_SEARCH_EXCEPTIONS = {"admin"}

def extract_keyword(question):
    text = correct_common_typos(question or "")

    # Date-range phrases describe the query window, never an item name.
    text = re.sub(
        r"(?:최근|지난)\s*(?:\d+|한|일|두|이|세|삼|네|사)\s*(?:일|주|개월|달)(?:\s*동안)?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:\d+|한|일|두|이|세|삼|네|사)\s*(?:일|주|개월|달)\s*(?:동안|간|치|전부터)",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?:이번|저번|지난)\s*(?:주|달|개월)", " ", text, flags=re.IGNORECASE)

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

    code = [
        c for c in re.findall(
            r"\b[A-Za-z0-9][A-Za-z0-9_\-./]*(?:\s+[A-Za-z0-9][A-Za-z0-9_\-./]*)*\b",
            code_source,
        )
        if re.search(r"\d", c) and len(c) >= 3
    ]
    if code:
        return max(code, key=len).strip()

    cleaned = re.sub(r"[?.,!<>()]", " ", translate_product_terms(text))

    for word in sorted(set(STOPWORDS) | set(MEANING_WORDS), key=len, reverse=True):
        cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)

    for keywords, _ in PAGE_KEYWORDS + DOMAIN_KEYWORDS:
        for keyword in keywords:
            cleaned = re.sub(re.escape(keyword), " ", cleaned, flags=re.IGNORECASE)

    cleaned = PARTICLE_PATTERN.sub(" ", cleaned)

    compact = " ".join(cleaned.split())

    # Korean sentence endings must not become database search keywords.
    # e.g. "수불재고 원자재 총 몇개야?" previously searched for item "야".
    compact = re.sub(
        r"(?:이야|야|인가요|인가|일까요|나요|니|죠|지요|예요|이에요)$",
        "",
        compact,
    ).strip()

    filler_tokens = {
        "가", "이", "은", "는", "을", "를", "에", "의", "중", "좀", "만",
        "입니까", "있", "있나요", "있어", "있음", "남음", "남았어", "돼", "됨",
    }
    compact = " ".join(
        token for token in compact.split()
        if token not in filler_tokens
    ).strip()

    return compact[:80]

def resolve_tool(question):
    text = normalize(question)

    if not text:
        return {"tool": "general.chat", "arguments": {"question": question or ""}}

    compact_text = re.sub(r"\s+", "", text)
    invalid_date_message = invalid_explicit_date(question)
    if invalid_date_message:
        return {"tool": "assistant.invalid_request", "arguments": {"message": invalid_date_message}}

    if "말고" not in compact_text and any(joiner in compact_text for joiner in ("이랑", "하고", "및", "둘다")):
        mixed_choices = []
        if any(marker in compact_text for marker in ("수불", "창고재고", "외주재고", "제공재고")):
            mixed_choices.append({"label": "수불 재고", "tool": "inventory.search", "arguments": {"item": "", "warehouse_type": "", "category": "", "grade": "", "lot": "", "limit": 15}})
        if "가계상" in compact_text:
            mixed_choices.append({"label": "가계상 재고", "tool": "stock.summary", "arguments": {"item": "", "category": "", "sort": "", "order": "asc", "limit": 15}})
        if "bom" in text or "자재명세" in text:
            mixed_choices.append({"label": "BOM", "tool": "bom.detail", "arguments": {"item": ""}})
        if "생산계획" in compact_text:
            mixed_choices.append({"label": "생산계획", "tool": "production.plan", "arguments": {"item": "", "period": "all"}})
        if "mrp" in text:
            mixed_choices.append({"label": "MRP 부족자재", "tool": "mrp.shortage_search", "arguments": {"sort": "desc", "limit": 5}})
        if len(mixed_choices) > 1 and "생산가능" not in compact_text:
            return {"tool": "assistant.clarify", "arguments": {
                "prompt": "여러 업무 영역이 함께 언급되었습니다. 어느 항목부터 확인할까요?",
                "choices": mixed_choices,
            }}

    explicit_inventory = has_inventory_context(text)
    after_malgo = compact_text.split("말고", 1)[1] if "말고" in compact_text else ""
    preferred_inventory = bool(after_malgo and any(marker in after_malgo for marker in ("수불", "창고", "외주", "제공")))
    preferred_stock = bool(after_malgo and "가계상" in after_malgo)
    explicit_stock = "가계상" in text and not preferred_inventory
    explicit_logistics = contains_any(text, ("제품 물류", "제품물류", "시리얼"))

    ambiguous_days = bare_day_count(question)
    if ambiguous_days and (explicit_inventory or explicit_stock or explicit_logistics) and contains_any(text, ("입고", "출고", "입출고", "이력", "내역", "현황")):
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        try:
            exact = date(today.year, today.month, ambiguous_days)
        except ValueError:
            exact = None
        selected_tool = "inventory.movement_search" if explicit_inventory else "stock.movement_search" if explicit_stock else "logistics.flow_count"
        def period_arguments(period_value):
            if selected_tool == "inventory.movement_search":
                return {"item": "", "warehouse_type": "", "movement_type": "", "period": period_value, "limit": 15}
            if selected_tool == "stock.movement_search":
                return {"item": "", "movement_type": "", "period": period_value, "limit": 15}
            return {"flow_type": "both", "product": extract_product(question), "period": period_value, "keyword": ""}
        choices = [{
            "label": f"최근 {ambiguous_days}일",
            "tool": selected_tool,
            "arguments": period_arguments(f"last_{ambiguous_days}_days"),
        }]
        if exact:
            choices.append({
                "label": f"{exact.month}월 {exact.day}일 하루",
                "tool": selected_tool,
                "arguments": period_arguments(f"date_{exact:%Y%m%d}"),
            })
        return {
            "tool": "assistant.clarify",
            "arguments": {"prompt": f"'{ambiguous_days}일'은 기간인가요, 날짜인가요?", "choices": choices},
        }

    if (
        "입출고현황" in compact_text
        and not (explicit_inventory or explicit_stock or explicit_logistics or "총재고" in compact_text)
    ):
        return {
            "tool": "assistant.clarify",
            "arguments": {
                "prompt": "어느 영역의 입출고 현황을 확인할까요?",
                "choices": [
                    {"label": "제품 물류 입출고", "tool": "logistics.flow_count", "arguments": {"flow_type": "both", "product": "", "period": extract_period(question), "keyword": ""}},
                    {"label": "수불 재고 입출고", "tool": "inventory.movement_search", "arguments": {"item": "", "warehouse_type": "", "movement_type": "", "period": extract_period(question)}},
                    {"label": "가계상 재고 입출고", "tool": "stock.movement_search", "arguments": {"item": "", "movement_type": "", "period": extract_period(question)}},
                ],
            }
        }

    if (
        "재고현황" in compact_text
        and not (explicit_inventory or explicit_stock or "총재고" in compact_text)
        and not contains_any(text, ("입고", "출고", "입출고"))
    ):
        return {
            "tool": "assistant.clarify",
            "arguments": {
                "prompt": "어느 재고 현황을 확인할까요?",
                "choices": [
                    {"label": "수불 재고", "tool": "inventory.search", "arguments": {"item": "", "warehouse_type": "", "category": "", "grade": "", "lot": "", "limit": 15}},
                    {"label": "가계상 재고", "tool": "stock.summary", "arguments": {"item": "", "category": "", "sort": "", "order": "asc", "limit": 15}},
                ],
            }
        }

    if (
        "lot" in text
        and has_inventory_context(text)
        and contains_any(text, ("현황", "목록", "보여", "알려", "조회"))
        and not contains_any(text, ("입고", "출고", "입출고"))
        and not re.search(r"lot\s*[A-Za-z]*\d+", question or "", re.IGNORECASE)
    ):
        return {
            "tool": "inventory.lot_summary",
            "arguments": {}
        }

    workflow_department = extract_workflow_department(text)
    if (
        workflow_department
        and not contains_any(text, ("workflow", "워크플로우"))
        and contains_any(text, ("멈춰", "머물", "대기", "진행", "번호", "단계", "상태"))
    ):
        keyword = extract_scoped_keyword(question, (
            "품질팀", "구매팀", "자재팀", "생산팀", "품질부서", "구매부서", "자재부서", "생산부서",
            "멈춰있는", "멈춰", "머물러있는", "머물", "대기중인", "대기", "진행중인", "진행", "번호", "단계", "상태",
        ))
        if workflow_department == "production":
            return {"tool": "assistant.clarify", "arguments": {
                "prompt": "'생산팀'이 Workflow 생산 부서를 뜻하나요, 아니면 생산계획을 뜻하나요?",
                "choices": [
                    {"label": "Workflow 생산팀 진행 현황", "tool": "workflow.status", "arguments": {
                        "item": keyword, "status": "IN_PROGRESS", "department": "production", "limit": 15,
                    }},
                    {"label": "생산계획", "tool": "production.plan", "arguments": {
                        "item": "", "period": "all",
                    }},
                ],
            }}
        return {"tool": "workflow.status", "arguments": {
            "item": keyword, "status": "IN_PROGRESS", "department": workflow_department, "limit": 15,
        }}

    if contains_any(text, ("workflow", "워크플로우")) and contains_any(
        text, ("단계", "상태", "진행", "어디", "대기", "완료", "부서", "멈춰", "머물")
    ):
        status = "COMPLETED" if "완료" in text else "IN_PROGRESS" if contains_any(text, ("진행", "대기", "멈춰", "머물")) else ""
        department = workflow_department
        keyword = extract_scoped_keyword(question, (
            "workflow", "워크플로우", "단계", "상태", "진행되고", "진행중", "진행", "되고", "되어", "어디", "어느", "지금", "현재",
            "대기", "완료", "멈춰있는", "멈춰", "머물러있는", "부서", "품질팀", "구매팀", "자재팀", "생산팀", "번호", "중에", "것",
        ))
        return {"tool": "workflow.status", "arguments": {"item": keyword, "status": status, "department": department, "limit": 15}}

    if contains_any(text, ("workflow", "워크플로우")) and contains_any(text, ("번호", "찾", "조회", "알려")):
        return {
            "tool": "workflow.search",
            "arguments": {
                "item": extract_workflow_item(question),
                "service_type": extract_product(question),
            }
        }

    if asks_capabilities(text):
        return {
            "tool": "assistant.capabilities",
            "arguments": {}
        }

    if asks_upload_help(text):
        return {
            "tool": "project.upload_help",
            "arguments": {"question": question}
        }

    if contains_any(text, ("대여", "렌탈")) and not wants_move(text):
        rental_keyword = extract_scoped_keyword(question, (
            "대여", "렌탈", "재고", "입고", "출고", "입출고", "이력", "내역", "현황",
        ))
        if contains_any(text, ("입고", "출고", "입출고", "이력", "내역")):
            return {"tool": "rental.movement_search", "arguments": {
                "item": rental_keyword, "movement_type": extract_movement_type(text),
                "period": extract_period(question), "limit": 15,
            }}
        return {"tool": "rental.summary", "arguments": {"item": rental_keyword, "category": "", "limit": 15}}

    if contains_any(text, ("품목 변경", "품목변경", "코드 변경", "품명 변경", "리비전 변경", "rev 변경", "품목명 바뀐", "품명이 바뀐")):
        keyword = extract_scoped_keyword(question, (
            "품목", "품목명", "코드", "품명", "리비전", "rev", "변경", "바뀐", "이력", "내역", "기록",
        ))
        return {"tool": "item.master_history", "arguments": {"item": keyword}}

    if asks_unsupported_analysis(text):
        return {
            "tool": "assistant.analysis_limit",
            "arguments": {"question": question}
        }

    shortage_word = contains_any(text, ("부족", "모자란", "모자라"))
    asks_shortage_materials = shortage_word and contains_any(
        text, ("mrp", "자재", "품목", "재고", "수량")
    )

    if asks_shortage_materials:

        number = extract_number(question)
        compact_shortage = re.sub(r"\s+", "", text)

        if any(phrase in compact_shortage for phrase in (
            "총몇개", "몇개", "몇건", "품목수", "자재수", "개수",
        )) and not contains_any(text, ("top", "상위")):
            return {"tool": "mrp.shortage_summary", "arguments": {"mode": "count"}}

        if any(phrase in compact_shortage for phrase in (
            "총수량", "수량합계", "부족수량합", "수량얼마",
        )):
            return {"tool": "mrp.shortage_summary", "arguments": {"mode": "qty"}}

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

        if contains_any(text, ("가장", "제일", "최대", "많은", "높은", "큰")):
            return {
                "tool": "mrp.shortage_max",
                "arguments": {}
            }

        return {
            "tool": "mrp.shortage_search",
            "arguments": {
                "sort": "desc",
                "limit": 5,
            }
        }

    if contains_any(text, ("생산계획", "생산 계획", "production plan")):
        if "제품" in text and contains_any(text, ("있는", "목록", "어떤", "알려", "보여", "뭐")):
            return {
                "tool": "production.products",
                "arguments": {"period": extract_period(question)}
            }
        return {
            "tool": "production.plan",
            "arguments": {
                "item": extract_keyword(question),
                "period": extract_period(question),
            }
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

    if contains_any(text, ("serial", "시리얼")) and contains_any(
        text, ("이동", "경로", "이력", "기록", "조회", "찾")
    ):
        item = extract_scoped_keyword(question, (
            "serial", "시리얼", "이동", "경로", "이력", "기록", "조회", "찾아줘", "찾기",
        ))
        return {"tool": "movement.search", "arguments": {"item": item}}

    if wants_move(text):
        page = extract_page(question)
        target = extract_keyword(question)
        if page and re.sub(r"\s+", "", target.lower()) in {
            "대여", "렌탈", "workflow", "워크플로우", "재고", "이력", "입출고",
        }:
            target = ""

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

    flow_words = ("입고", "출고", "inbound", "outbound", "나갔", "내보", "들어왔", "들어온")

    if contains_any(text, flow_words):
        movement_type = extract_movement_type(text)
        period = extract_period(question)
        asks_single = contains_any(text, ("최신", "마지막", "하나", "한 개")) or (
            "최근" in text and not is_rolling_period(period)
        )
        limit = 1 if asks_single else 15

        if has_inventory_context(text) or "lot" in text:
            return {
                "tool": "inventory.movement_search",
                "arguments": {
                    "item": "",
                    "warehouse_type": extract_warehouse_type(text),
                    "movement_type": movement_type,
                    "period": period,
                    "limit": limit,
                    "require_lot": "lot" in text,
                }
            }

        if "가계상" in text:
            return {
                "tool": "stock.movement_search",
                "arguments": {
                    "item": "",
                    "movement_type": movement_type,
                    "period": period,
                    "limit": limit,
                }
            }

        if contains_any(text, ("총 재고", "총재고", "재고 현황", "재고현황")):
            return {
                "tool": "stock.combined_movement_search",
                "arguments": {
                    "movement_type": movement_type,
                    "period": period,
                    "limit": limit,
                }
            }

    if contains_any(text, flow_words):
        matched = [kw for kw in flow_words if kw in text]
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

    if (preferred_inventory or "가계상" not in text) and has_inventory_context(text):
        matched = [
            kw for kw in ("수불 재고", "수불재고", "계상 재고", "계상재고", "창고재고", "제공재고", "외주재고")
            if kw in text
        ]

        warehouse_type = extract_warehouse_type(text)

        grade = ""
        grade_match = re.search(r"\b([ABF])\s*등급|등급\s*([ABF])\b", question or "", re.IGNORECASE)
        if grade_match:
            grade = (grade_match.group(1) or grade_match.group(2)).upper()

        lot = ""
        lot_match = re.search(r"lot\s*([A-Za-z]*\d+)", question or "", re.IGNORECASE)
        if lot_match:
            lot = lot_match.group(1)
        else:
            # In an explicit inventory question, codes such as F25/G23 are
            # commonly LOT values even when the user omits the word "LOT".
            lot_match = re.search(r"(?<![A-Za-z0-9_-])([A-Za-z]\d{2,})(?![A-Za-z0-9_-])", question or "")
            if lot_match:
                lot = lot_match.group(1)

        scrubbed = re.sub(
            r"(?i)[ABF]\s*등급|등급\s*[ABF]|lot\s*[A-Za-z]*\d*",
            " ",
            question or ""
        )
        if lot:
            scrubbed = re.sub(rf"(?<![A-Za-z0-9_-]){re.escape(lot)}(?![A-Za-z0-9_-])", " ", scrubbed, flags=re.IGNORECASE)

        sort, order = extract_sort(question)
        category = extract_stock_category(question)
        item = "" if sort else remove_inventory_scope_words(
            extract_keyword(scrubbed),
            category,
        )

        return _meaning_or(matched, {
            "tool": "inventory.search",
            "arguments": {
                "item": item,
                "warehouse_type": warehouse_type,
                "category": category,
                "grade": grade,
                "lot": lot,
                "sort": sort,
                "order": order,
                "limit": 1 if sort else 15,
            }
        })

    if not preferred_inventory and contains_any(text, ("가계상", "반제품", "원자재", "제품", "재고")):
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
            item = extract_keyword(question)
            generic_terms = {
                "material.master": {"자재", "자재 정보", "기준정보", "정보"},
                "bom.detail": {"bom", "부품", "구성품", "자재명세"},
                "item.master": {"품목", "품목 정보", "정보", "기준정보"},
                "movement.search": {"시리얼", "이동", "경로", "이력"},
            }
            if item.lower() in {value.lower() for value in generic_terms.get(tool, set())}:
                item = ""

            return _meaning_or(matched, {
                "tool": tool,
                "arguments": {
                    "item": item
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

    if looks_like_conversation(text):
        return {
            "tool": "assistant.smalltalk",
            "arguments": {"question": question}
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
