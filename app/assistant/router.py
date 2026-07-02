from app.assistant.registry import TOOLS


class ToolRouter:

    def __init__(self, db):
        self.db = db

    def execute(self, tool_data):
        if not isinstance(tool_data, dict):
            return {
                "success": False,
                "message": "요청 형식이 올바르지 않습니다."
            }

        tool = tool_data.get("tool")
        arguments = tool_data.get("arguments", {})

        if not isinstance(arguments, dict):
            arguments = {}

        if tool not in TOOLS:
            return {
                "success": False,
                "message": "지원하지 않는 요청입니다."
            }

        func = TOOLS[tool]

        try:
            return func(db=self.db, **arguments)
        except TypeError:
            return {
                "success": False,
                "message": "요청 인자가 올바르지 않습니다."
            }
