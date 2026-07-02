from app.assistant.registry import tool


@tool("system.ping")
def ping(db=None):

    return {
        "success": True,
        "message": "AI Tool Engine 정상 작동"
    }