import re

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
    if any(term in compact for term in ("수불재고", "계상재고", "창고재고", "제공재고", "외주재고")):
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
        r"(?i)workflow|워크플로우|번호|부여된|부여|지금|현재|알려줘|알려주세요|찾아줘|찾기|검색|조회",
        " ",
        value,
    )
    value = re.sub(r"[?.,!]", " ", value)
    value = re.sub(r"(?:에|의|은|는|이|가)$", "", " ".join(value.split()))
    return value.strip()

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

    if "입출고" in lowered:
        return "both"

    if "출고" in lowered or "outbound" in lowered or "나갔" in lowered or "내보" in lowered:
        return "outbound"

    if "입고" in lowered or "inbound" in lowered or "들어왔" in lowered or "들어온" in lowered:
        return "inbound"

    return "both"

def extract_movement_type(text):

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

    if (
        "lot" in text
        and has_inventory_context(text)
        and contains_any(text, ("현황", "목록", "보여", "알려", "조회"))
        and not re.search(r"lot\s*[A-Za-z]*\d+", question or "", re.IGNORECASE)
    ):
        return {
            "tool": "inventory.lot_summary",
            "arguments": {}
        }

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

    if asks_unsupported_analysis(text):
        return {
            "tool": "assistant.analysis_limit",
            "arguments": {"question": question}
        }

    asks_shortage_materials = "부족" in text and contains_any(
        text, ("mrp", "자재", "품목", "재고")
    )

    if asks_shortage_materials:

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

    if "가계상" not in text and has_inventory_context(text):
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

    if looks_like_conversation(text):
        return {
            "tool": "general.chat",
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
