from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from app.database import SessionLocal
import re
from app.models.outbound import Outbound
from app.models.inbound import Inbound
from fastapi.responses import RedirectResponse
from datetime import date
from app.models.movement import Movement
from fastapi import Request
from app.utils.logger import save_log

SERVICE_NAMES = {
    "cart_bp_pro": "CART BP pro",
    "cart_bp": "CART BP",
    "cart_on": "CART ON",
    "hanbang": "한방 병원",
    "cart_platform" : "CART PLATFORM",
    "cart_ring" : "CART RING",
    "cart_o2" : "CART O2"
}

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def root():
    return RedirectResponse(
        "/product/cart_bp_pro/outbound"
    )

@router.post("/scan")
async def scan(request: Request, data: dict):
    username = request.session.get("user", "unknown")
    raw = data.get("qr")
    product = data.get("product")
    mode = data.get("mode")

    match = re.search(r"[A-Z]\d{6}-[A-Z0-9]{5}", raw)
    if not match:
        return {"status": "error"}

    serial = match.group().upper()

    db = SessionLocal()

    # 🔥 출고
    if mode == "outbound":
        exists = db.query(Outbound)\
            .filter(Outbound.serial == serial)\
            .first()

        if exists:
            db.close()
            return {
                "status": "duplicate",
                "serial": serial
            }

        db.add(Outbound(
            serial=serial,
            product=product,
            size=None,
            category=None
        ))

        db.add(Movement(
            serial=serial,
            product=product,
            type="OUT",
            source="scan",
            client=None,
            category=None,
            user=username
        ))

    # 🔥 입고
    elif mode == "inbound":
        exists = db.query(Inbound)\
            .filter(Inbound.serial == serial)\
            .first()

        if exists:
            db.close()
            return {
                "status": "duplicate",
                "serial": serial
            }

        db.add(Inbound(
            serial=serial,
            product=product,
            created_at=date.today(),
            size=None,
            category=None
        ))

        db.add(Movement(
            serial=serial,
            product=product,
            type="IN",
            source="scan",
            client=None,
            category=None,
            user=username
        ))

    db.commit()

    service_name = SERVICE_NAMES.get(
        product,
        product
    )

    if mode == "outbound":

        save_log(
            user=username,
            product=service_name,
            action="OUTBOUND",
            serial=serial,
            detail="QR 출고 처리"
        )

    elif mode == "inbound":

        save_log(
            user=username,
            product=service_name,
            action="INBOUND",
            serial=serial,
            detail="QR 입고 처리"
        )

    new_item = db.query(Outbound if mode=="outbound" else Inbound)\
        .filter_by(serial=serial)\
        .first()
    
    db.close()

    return {
        "status": "ok",
        "serial": serial,
        "id": new_item.id,
        "size": new_item.size,
        "created_at": str(new_item.created_at)
    }