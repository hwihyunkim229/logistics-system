from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.workflow.utils import get_db
from app.workflow.services.remnant_service import restock_remnant

router = APIRouter(
    prefix="/workflow/remnant",
    tags=["Workflow Remnant"],
)


@router.post("/{remnant_id}/restock")
def restock(
    remnant_id: int,
    request: Request,
    redirect_to: str = Form("/workflow/production"),
    db: Session = Depends(get_db),
):
    user = request.session.get("user", "SYSTEM")

    try:
        restock_remnant(
            db,
            remnant_id=remnant_id,
            restocked_by=user,
        )
    except Exception as e:
        return RedirectResponse(
            f"{redirect_to}?error={quote(str(e))}",
            status_code=303,
        )

    return RedirectResponse(redirect_to, status_code=303)
