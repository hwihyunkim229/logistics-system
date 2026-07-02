from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import Request
from app.database import SessionLocal
from app.assistant.agent import AssistantAgent

router = APIRouter()


@router.post("/assistant/chat")
async def assistant_chat(
    request: Request,
    question: str
):

    session_id = request.session.get("user")
    role = request.session.get("role", "user")

    db = SessionLocal()

    try:

        agent = AssistantAgent(db)

        result = agent.chat(
            question,
            session_id,
            role
        )

        return JSONResponse(result)

    finally:

        db.close()