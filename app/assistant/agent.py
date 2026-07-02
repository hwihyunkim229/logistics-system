import re

from app.ai.responder import make_answer
from app.assistant.memory import memory
from app.assistant.query_router import resolve_tool
from app.assistant.router import ToolRouter
import app.assistant.tools


ADMIN_ONLY_TOOLS = {
    "admin.user_summary",
    "admin.account_action",
    "activity.search",
    "activity.login_summary",
}


class AssistantAgent:

    def __init__(self, db):
        self.router = ToolRouter(db)

    def chat(self, question: str, session_id: str, role: str = "user"):
        selected_tool = self._resolve_follow_up(question, session_id)

        if selected_tool is None:
            selected_tool = resolve_tool(question)

        if selected_tool.get("tool") in ADMIN_ONLY_TOOLS and role != "admin":
            return {
                "type": "text",
                "message": "사용자 계정과 활동 로그 조회는 관리자만 사용할 수 있습니다."
            }

        result = self.router.execute(selected_tool)

        if result.get("status") in ("rows", "global_search"):
            rows = result.get("rows", [])
            if isinstance(rows, list) and rows:
                memory.save(
                    session_id,
                    selected_tool["tool"],
                    rows
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
        match = re.search(r"(\d+)\s*(번|번째)", question or "")

        if not match:
            return None

        saved = memory.get(session_id)

        if not saved:
            return None

        index = int(match.group(1)) - 1

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

        return {
            "tool": saved["tool"],
            "arguments": {
                "item": item
            }
        }
