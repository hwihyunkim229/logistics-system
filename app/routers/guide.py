from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/guide", name="operations_guide")
async def operations_guide(request: Request):
    """로그인한 사용자가 공통 운영가이드를 확인한다."""
    return templates.TemplateResponse(
        request=request,
        name="guide/operations.html",
    )
