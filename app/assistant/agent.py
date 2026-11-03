import re
from app.ai.responder import make_answer
from app.assistant.memory import memory
from app.assistant.query_router import (
    extract_movement_type,
    extract_period,
    resolve_tool,
    wants_move,
)
from app.assistant.router import ToolRouter
import app.assistant.tools
from app.ai.planner import ai_resolve_tool

FOLLOW_UP_PRONOUNS = ("거기", "그거", "그것", "저기", "그 품목", "그 항목")

PAGE_FOLLOW_UP_PRONOUNS = ("그 페이지", "이 페이지", "그 화면", "이 화면")

TOOL_TO_PAGE = {
    "stock.summary": "stock",
    "stock.book": "stock",
    "inventory.search": "inventory",
    "bom.detail": "bom",
    "production.plan": "production_plan",
    "material.master": "material_master",
    "item.master": "item_master",
    "movement.search": "stock_history",
    "activity.search": "activity",
    "admin.user_summary": "users",
}

ADMIN_ONLY_TOOLS = {
    "admin.user_summary",
    "admin.account_action",
    "activity.search",
    "activity.login_summary",
}

GENERIC_FALLBACK_TOOLS = {
    "general.chat",
    # A low-confidence global search is kept as the no-AI fallback, but an
    # available planner gets one chance to understand unusual phrasing.
    "global.search",
}

CONTEXT_PRESERVING_TOOLS = {
    "inventory.search", "inventory.lot_summary", "inventory.movement_search",
    "stock.summary", "stock.movement_search", "stock.combined_movement_search",
    "logistics.flow_count", "rental.summary", "rental.movement_search",
    "mrp.shortage_search", "mrp.shortage_summary", "mrp.dashboard",
    "bom.detail", "production.plan", "production.products",
    "material.master", "item.master", "item.master_history",
    "workflow.search", "workflow.status", "movement.search",
    "activity.search", "activity.login_summary", "admin.user_summary",
    "project.upload_help", "system.summary",
}

FOLLOWUP_DETAIL_MARKERS = (
    "수량", "개수", "몇개", "몇건", "합계", "총", "더", "다시",
    "그럼", "그러면", "그거", "그건", "이건", "그중", "목록", "상세",
    "업체", "공급사", "리드타임", "납기", "moq", "rev", "리비전",
    "lot", "grade", "등급", "단계", "상태", "부서", "담당", "날짜",
    "언제", "필수", "선택", "컬럼", "열", "이력", "내역",
)

class AssistantAgent:

    def __init__(self, db):
        self.router = ToolRouter(db)

    def chat(self, question: str, session_id: str, role: str = "user"):
        selected_tool = self._resolve_follow_up(
            question,
            session_id
        )

        if selected_tool is None:

            selected_tool = resolve_tool(question)

            if selected_tool.get("tool") in GENERIC_FALLBACK_TOOLS:
                ai_tool = ai_resolve_tool(question)

                if ai_tool is not None:
                    selected_tool = ai_tool

        if selected_tool.get("tool") in ADMIN_ONLY_TOOLS and role != "admin":
            return {
                "type": "text",
                "message": "사용자 계정과 활동 로그 조회는 관리자만 사용할 수 있습니다."
            }

        result = self.router.execute(selected_tool)
        memory.save_context(
            session_id,
            selected_tool.get("tool", ""),
            selected_tool.get("arguments", {}),
        )

        if result.get("status") in ("rows", "global_search", "stock_summary"):
            rows = result.get("rows", [])
            if isinstance(rows, list) and rows:
                memory.save(
                    session_id,
                    selected_tool["tool"],
                    rows
                )
        elif result.get("status") == "need_page_choice":
            memory.save(
                session_id,
                "page.choice",
                result.get("choices", [])
            )
        elif result.get("status") == "need_clarification":
            memory.save(
                session_id,
                "assistant.clarification",
                result.get("choices", []),
            )
        elif result.get("type") == "move" and selected_tool.get("tool") in (
            "page.move", "page.find", "page.choice"
        ):
            page = selected_tool.get("arguments", {}).get("page", "")
            if page:
                memory.save(session_id, "page.context", [{"page": page}])

        answer = make_answer(question, result)

        response_type = result.get("type", "text")

        response = {
            "type": response_type,
            "message": answer
        }

        if response_type == "move":
            response["url"] = result.get("url")

        return response

    def _resolve_follow_up(self, question: str, session_id: str):
        text = question or ""
        saved = memory.get(session_id)
        context = memory.get_context(session_id)

        movement_tools = {
            "inventory.movement_search",
            "stock.movement_search",
            "stock.combined_movement_search",
            "rental.movement_search",
            "logistics.flow_count",
        }
        compact = re.sub(r"\s+", "", text.lower())
        explicit_domain = any(marker in compact for marker in (
            "수불", "가계상", "총재고", "전체재고", "대여", "렌탈",
            "제품물류", "시리얼", "workflow", "워크플로우",
        ))
        followup_period = extract_period(text)
        has_period_phrase = followup_period != "all"
        has_flow_phrase = any(marker in compact for marker in (
            "입고", "출고", "입출고", "들어온", "들어왔", "나간", "나갔",
        ))

        if context and context.get("tool") == "mrp.shortage_summary":
            if any(marker in compact for marker in ("수량", "합계", "얼마")):
                return {"tool": "mrp.shortage_summary", "arguments": {"mode": "qty"}}
            if any(marker in compact for marker in ("몇개", "몇건", "개수", "품목수", "자재수")):
                return {"tool": "mrp.shortage_summary", "arguments": {"mode": "count"}}

        if context and context.get("tool") == "mrp.shortage_search":
            if any(marker in compact for marker in ("총수량", "수량합계", "합계", "전체수량")):
                return {"tool": "mrp.shortage_summary", "arguments": {"mode": "qty"}}
            if any(marker in compact for marker in ("총몇개", "몇건", "품목수", "자재수", "개수")):
                return {"tool": "mrp.shortage_summary", "arguments": {"mode": "count"}}
            top_match = re.search(r"(?:상위|top)\s*(\d+)", text, re.IGNORECASE)
            if top_match:
                arguments = dict(context.get("arguments", {}))
                arguments["limit"] = max(1, min(int(top_match.group(1)), 15))
                return {"tool": "mrp.shortage_search", "arguments": arguments}

        if context and context.get("tool") in ("workflow.search", "workflow.status"):
            department = ""
            for markers, value in (
                (("품질팀", "품질부서", "quality"), "quality"),
                (("구매팀", "구매부서", "purchase"), "purchase"),
                (("자재팀", "자재부서", "material"), "material"),
                (("생산팀", "생산부서", "production"), "production"),
            ):
                if any(marker in compact for marker in markers):
                    department = value
                    break
            if department:
                previous = dict(context.get("arguments", {}))
                return {
                    "tool": "workflow.status",
                    "arguments": {
                        "item": previous.get("item", ""),
                        "status": previous.get("status", "IN_PROGRESS") or "IN_PROGRESS",
                        "department": department,
                        "limit": previous.get("limit", 15),
                    },
                }

        if context and context.get("tool") in movement_tools and "수불" in compact:
            previous_tool = context["tool"]
            previous = dict(context.get("arguments", {}))
            if previous_tool == "logistics.flow_count":
                movement_type = {
                    "inbound": "IN", "outbound": "OUT",
                }.get(previous.get("flow_type"), "")
            else:
                movement_type = previous.get("movement_type", "")
            return {
                "tool": "inventory.movement_search",
                "arguments": {
                    "item": previous.get("item", ""),
                    "warehouse_type": previous.get("warehouse_type", ""),
                    "movement_type": movement_type,
                    "period": previous.get("period", "all"),
                    "limit": previous.get("limit", 1),
                    "require_lot": bool(previous.get("require_lot") or "lot" in compact),
                },
            }

        if context and context.get("tool") in movement_tools and "가계상" in compact:
            previous = dict(context.get("arguments", {}))
            movement_type = previous.get("movement_type", "")
            if context["tool"] == "logistics.flow_count":
                movement_type = {"inbound": "IN", "outbound": "OUT"}.get(previous.get("flow_type"), "")
            return {
                "tool": "stock.movement_search",
                "arguments": {
                    "item": previous.get("item", ""),
                    "movement_type": movement_type,
                    "period": previous.get("period", "all"),
                    "limit": previous.get("limit", 1),
                },
            }

        if (
            context
            and context.get("tool") in CONTEXT_PRESERVING_TOOLS
            and context.get("tool") not in movement_tools
        ):
            tool = context["tool"]
            domain_markers = {
                "inventory": ("수불", "창고재고", "외주재고", "제공재고"),
                "stock": ("가계상",),
                "logistics": ("제품물류",),
                "rental": ("대여", "렌탈"),
                "mrp": ("mrp", "부족자재"),
                "bom": ("bom", "자재명세"),
                "production": ("생산계획",),
                "material": ("자재기준",),
                "item": ("품목기준", "품목관리"),
                "workflow": ("workflow", "워크플로우"),
                "activity": ("활동로그",),
                "admin": ("사용자계정", "계정관리"),
            }
            mentioned_domains = {
                prefix for prefix, markers in domain_markers.items()
                if any(marker in compact for marker in markers)
            }
            current_prefix = tool.split(".", 1)[0]
            switches_domain = mentioned_domains and current_prefix not in mentioned_domains
            is_short_followup = len(compact) <= 35 and any(
                marker in compact for marker in FOLLOWUP_DETAIL_MARKERS
            )
            if is_short_followup and not switches_domain:
                arguments = dict(context.get("arguments", {}))
                if tool == "project.upload_help":
                    original = arguments.get("question", "")
                    arguments["question"] = f"{original} {text}".strip()
                elif tool == "workflow.search" and any(marker in compact for marker in ("단계", "상태", "부서", "담당")):
                    return {
                        "tool": "workflow.status",
                        "arguments": {"item": arguments.get("item", ""), "status": "", "limit": 15},
                    }
                return {"tool": tool, "arguments": arguments}

        if (
            context
            and context.get("tool") in movement_tools
            and not explicit_domain
            and "lot" not in compact
            and (has_period_phrase or has_flow_phrase)
        ):
            tool = context["tool"]
            arguments = dict(context.get("arguments", {}))
            if has_period_phrase:
                arguments["period"] = followup_period

            movement_type = extract_movement_type(text)
            if tool == "logistics.flow_count":
                if movement_type == "IN":
                    arguments["flow_type"] = "inbound"
                elif movement_type == "OUT":
                    arguments["flow_type"] = "outbound"
                elif "입출고" in compact:
                    arguments["flow_type"] = "both"
            else:
                if movement_type or "입출고" in compact:
                    arguments["movement_type"] = movement_type
                if has_period_phrase:
                    arguments["limit"] = 15
                elif "최근" in compact:
                    arguments["limit"] = 1

            return {"tool": tool, "arguments": arguments}

        if context and any(phrase in text.replace(" ", "") for phrase in (
            "알려달라고", "다시알려", "다시보여", "확인해줘", "확인해주세요"
        )):
            tool = context.get("tool", "")
            arguments = dict(context.get("arguments", {}))
            return {"tool": tool, "arguments": arguments}

        if not saved:
            return None

        if saved["tool"] == "assistant.clarification":
            resolved = self._resolve_clarification(text, saved.get("items", []))
            if resolved is not None:
                return resolved
            return {
                "tool": "assistant.clarify",
                "arguments": {
                    "prompt": "선택한 항목을 확인하지 못했습니다. 아래 번호나 항목 이름으로 다시 답해 주세요.",
                    "choices": saved.get("items", []),
                },
            }

        if saved["tool"] == "page.context":
            previous_page = (saved.get("items") or [{}])[0].get("page", "")
            lowered = text.lower()
            if previous_page in ("mrp", "mrp_result") and any(
                word in lowered for word in ("result", "결과")
            ):
                return {
                    "tool": "page.move",
                    "arguments": {"page": "mrp_result"}
                }

        if (
            saved["tool"] in ("inventory.search", "inventory.lot_summary")
            and "lot" in text.lower()
            and any(word in text for word in ("보여", "현황", "목록", "알려", "조회"))
        ):
            return {
                "tool": "inventory.lot_summary",
                "arguments": {}
            }

        if saved["tool"] == "page.choice":
            resolved = self._resolve_page_choice(text, saved["items"])

            if resolved is not None:
                memory.clear(session_id)

            return resolved

        if any(pronoun in text for pronoun in PAGE_FOLLOW_UP_PRONOUNS):
            page = TOOL_TO_PAGE.get(saved["tool"])

            if page:
                return {
                    "tool": "page.move",
                    "arguments": {
                        "page": page
                    }
                }

            return None

        match = re.search(r"(\d+)\s*(번|번째)", text)

        if match:
            index = int(match.group(1)) - 1
        elif any(pronoun in text for pronoun in FOLLOW_UP_PRONOUNS):
            index = 0
        else:
            return None

        if index < 0 or index >= len(saved["items"]):
            return None

        selected = saved["items"][index]

        item = (
            selected.get("item_code")
            or selected.get("item_name")
            or selected.get("product_name")
            or selected.get("component_code")
            or ""
        )

        if wants_move(text):
            return {
                "tool": "page.find",
                "arguments": {
                    "page": "",
                    "target": item,
                }
            }

        return {
            "tool": saved["tool"],
            "arguments": {
                "item": item
            }
        }

    def _resolve_page_choice(self, text, choices):

        stripped = text.strip()

        match = re.fullmatch(r"(\d+)\s*(번|번째)?", stripped)

        index = None

        if match:
            index = int(match.group(1)) - 1
        else:
            normalized = stripped.replace(" ", "")

            for i, choice in enumerate(choices):
                label = (choice.get("label") or "").replace(" ", "")

                if label and label in normalized:
                    index = i
                    break

        if index is None or index < 0 or index >= len(choices):
            return None

        chosen = choices[index]

        return {
            "tool": "page.choice",
            "arguments": {
                "url": chosen.get("url", ""),
                "message": f"{chosen.get('label', '')}(으)로 이동합니다.",
            }
        }

    def _resolve_clarification(self, text, choices):
        stripped = (text or "").strip()
        match = re.fullmatch(r"(\d+)\s*(?:번|번째)?", stripped)
        if match is None:
            match = re.match(r"^(\d+)\s*(?:번|번째)(?:\s+|$)", stripped)
        index = int(match.group(1)) - 1 if match else None

        if index is None:
            normalized = re.sub(r"\s+", "", stripped).lower()
            clarification_aliases = {
                "수불": "수불재고",
                "창고": "수불재고",
                "계상": "수불재고",
                "장부": "가계상재고",
                "가계상": "가계상재고",
                "제품": "제품물류입출고",
                "물류": "제품물류입출고",
            }
            normalized = clarification_aliases.get(normalized, normalized)
            for i, choice in enumerate(choices):
                label = re.sub(r"\s+", "", choice.get("label", "")).lower()
                if label and (label in normalized or normalized in label):
                    index = i
                    break

        if index is None or index < 0 or index >= len(choices):
            return None

        choice = choices[index]
        return {
            "tool": choice.get("tool", "general.chat"),
            "arguments": dict(choice.get("arguments", {})),
        }
