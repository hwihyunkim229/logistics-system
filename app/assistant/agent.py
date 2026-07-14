import re
from app.ai.responder import make_answer
from app.assistant.memory import memory
from app.assistant.query_router import resolve_tool, wants_move
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
}

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

        if not saved:
            return None

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