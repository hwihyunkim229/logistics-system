from app.utils.filters import filter_values
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from math import ceil
from typing import Optional
import pandas as pd
from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.inventory_lot import InventoryLot
from app.models.item_master import ItemMaster
from app.models.stock import Stock
from app.utils.logger import save_log
from app.utils.downloads import download_content_disposition
from app.utils.item_codes import normalize_item_code
from app.utils.timezone import format_kst

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

INVENTORY_LOG_PRODUCT = "수불 재고"

WAREHOUSE_TYPES = ["창고재고", "제공재고", "외주재고"]
CATEGORIES = ["반제품", "제품", "원자재"]
GRADES = ["A", "B", "F"]


class InventoryMovementRequest(BaseModel):
    ids: list[int] = Field(min_length=1)
    qty: int = Field(gt=0)
    remark: str = Field(default="", max_length=500)
    lot: str = Field(default="", max_length=100)
    inspector: str = Field(default="", max_length=100)
    first_received_date: str = Field(default="", max_length=30)


def parse_first_received_date(value: str):
    text = (value or "").strip()
    if not text:
        return None
    normalized = (
        text.replace(" ", "")
        .replace("년", "-")
        .replace("월", "-")
        .replace("일", "")
        .replace(".", "-")
        .replace("/", "-")
        .rstrip("-")
    )
    if len(normalized) == 8 and normalized.isdigit():
        normalized = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        raise ValueError("입고일자는 YYYY-MM-DD 형식이어야 합니다.")


def inventory_lot_row(db, item, lot):
    return (
        db.query(InventoryLot)
        .filter(InventoryLot.inventory_id == item.id, InventoryLot.lot == lot)
        .first()
    )


def tracked_lot_qty(db, item_id):
    return int(
        db.query(func.coalesce(func.sum(InventoryLot.qty), 0))
        .filter(InventoryLot.inventory_id == item_id)
        .scalar()
        or 0
    )


def add_to_inventory_lot(db, item, lot, qty, first_received_date):
    row = inventory_lot_row(db, item, lot)
    if row is None:
        row = InventoryLot(
            inventory_id=item.id,
            item_code=item.item_code,
            warehouse_type=item.warehouse_type,
            grade=item.grade,
            lot=lot,
            first_received_date=first_received_date,
            qty=0,
        )
        db.add(row)
    elif first_received_date and (
        row.first_received_date is None or first_received_date < row.first_received_date
    ):
        row.first_received_date = first_received_date
    row.qty = (row.qty or 0) + qty
    return row

def parse_excel_quantity(value):
    """엑셀 수량을 정수로 변환하고 비어 있음을 뜻하는 값은 0으로 처리한다."""
    if pd.isna(value):
        return 0

    text = str(value).strip().replace(",", "")

    if text in {"", "-", "–", "—"}:
        return 0

    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("숫자로 변환할 수 없는 수량") from exc

    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError("수량은 정수여야 합니다")

    return int(number)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def current_user(request: Request):
    return request.session.get("user") or "system"

def summarize_items(items):
    codes = [item.item_code for item in items[:10]]

    suffix = (
        f" 외 {len(items) - 10}건"
        if len(items) > 10
        else ""
    )

    return ", ".join(codes) + suffix

def get_sub_category(item_name):

    name = (item_name or "").upper()

    if "RING" in name:
        return "RING"

    elif "CRADLE" in name:
        return "CRADLE"

    return "기타"

def get_raw_category(item_name):

    name = (item_name or "").upper()

    if (
        "PBA" in name
        and "RING" in name
        and (
            "ASS'Y" in name
            or "ASSY" in name
        )
    ):
        return "PBA"

    elif (
        "INNER" in name
        and "CRADLE" not in name
    ):
        return "INNER"

    elif (
        "OUTER" in name
        and "CRADLE" not in name
    ):
        return "OUTER"

    elif (
        (
            "TOP COVER" in name
            or "TOP" in name
        )
        and "CRADLE" not in name
    ):
        return "TOP COVER"

    return "사급자재"

def lookup_item_defaults(db, item_code):
    item_code = normalize_item_code(item_code)

    item_name = ""
    rev = ""
    category = ""

    master = (
        db.query(ItemMaster)
        .filter(ItemMaster.item_code == item_code)
        .first()
    )

    if not master:
        master = (
            db.query(ItemMaster)
            .filter(
                func.replace(
                    ItemMaster.item_code,
                    " ",
                    ""
                ) == item_code
            )
            .first()
        )

    if master:
        item_name = master.item_name or ""
        rev = master.rev or ""

    stock = (
        db.query(Stock)
        .filter(Stock.item_code == item_code)
        .first()
    )

    if not stock:
        stock = (
            db.query(Stock)
            .filter(
                func.replace(
                    Stock.item_code,
                    " ",
                    ""
                ) == item_code
            )
            .first()
        )

    if stock:
        category = stock.category or ""

        if not item_name:
            item_name = stock.item_name or ""

        if not rev:
            rev = stock.rev or ""

    return item_name, rev, category

def ensure_grade_siblings(db, item_code, warehouse_type, lot, category, item_name, rev):
    item_code = normalize_item_code(item_code)

    if warehouse_type != "창고재고":
        return

    for grade in GRADES:

        exists = (
            db.query(Inventory)
            .filter(
                func.replace(
                    Inventory.item_code,
                    " ",
                    ""
                ) == item_code,
                Inventory.warehouse_type == warehouse_type,
                Inventory.lot == lot,
                Inventory.grade == grade,
            )
            .first()
        )

        if exists:
            continue

        db.add(
            Inventory(
                item_code=item_code,
                item_name=item_name,
                category=category,
                warehouse_type=warehouse_type,
                lot=lot,
                grade=grade,
                rev=rev,
                qty=0,
            )
        )

@router.get("/inventory")
def inventory_page(
    request: Request,
    warehouse_type: str = "창고재고",
    category: str = "",
    keyword: str = "",
    grade: str = "",
    lot: str = "",
    rev: str = "",
    note: str = "",
    page: int = 1,
    db: Session = Depends(get_db)
):

    per_page = 50

    query = db.query(Inventory).filter(
        Inventory.warehouse_type == warehouse_type
    )

    if warehouse_type == "창고재고" and category:
        query = query.filter(Inventory.category == category)

    if keyword:
        query = query.filter(
            or_(
                Inventory.item_code.contains(keyword),
                Inventory.item_name.contains(keyword)
            )
        )

    scoped_rows = query.all()

    lots = sorted(
        {row.lot for row in scoped_rows if row.lot}
    )

    revs = sorted(
        {row.rev for row in scoped_rows if row.rev}
    )

    notes = sorted(
        {row.note for row in scoped_rows if row.note}
    )

    grade_values = filter_values(request, "grade")
    if grade_values:
        query = query.filter(Inventory.grade.in_(grade_values))

    lot_values = filter_values(request, "lot")
    if lot_values:
        query = query.filter(Inventory.lot.in_(lot_values))

    rev_values = filter_values(request, "rev")
    if rev_values:
        query = query.filter(Inventory.rev.in_(rev_values))

    note_values = filter_values(request, "note")
    if note_values:
        query = query.filter(Inventory.note.in_(note_values))

    total_count = query.count()

    items = (
        query
        .order_by(Inventory.item_code, Inventory.lot)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    lot_details_by_inventory = {}
    unclassified_by_inventory = {}
    if items:
        item_ids = [item.id for item in items if item.category == "원자재"]
        lot_rows = (
            db.query(InventoryLot)
            .filter(InventoryLot.inventory_id.in_(item_ids))
            .order_by(InventoryLot.first_received_date, InventoryLot.lot)
            .all()
            if item_ids
            else []
        )
        for row in lot_rows:
            lot_details_by_inventory.setdefault(row.inventory_id, []).append(row)
        for item in items:
            if item.category == "원자재":
                tracked = sum(row.qty or 0 for row in lot_details_by_inventory.get(item.id, []))
                unclassified_by_inventory[item.id] = max((item.qty or 0) - tracked, 0)

    total_pages = max(1, ceil(total_count / per_page))

    warehouse_totals = {}

    for wt in WAREHOUSE_TYPES:
        warehouse_totals[wt] = (
            db.query(func.coalesce(func.sum(Inventory.qty), 0))
            .filter(Inventory.warehouse_type == wt)
            .scalar()
        )

    return templates.TemplateResponse(
        request=request,
        name="inventory/index.html",
        context={
            "items": items,
            "current_warehouse_type": warehouse_type,
            "current_category": category,
            "keyword": keyword,
            "current_grade": grade,
            "current_lot": lot,
            "current_rev": rev,
            "current_note": note,
            "page": page,
            "total_pages": total_pages,
            "lots": lots,
            "revs": revs,
            "notes": notes,
            "warehouse_types": WAREHOUSE_TYPES,
            "categories": CATEGORIES,
            "grades": GRADES,
            "warehouse_totals": warehouse_totals,
            "lot_details_by_inventory": lot_details_by_inventory,
            "unclassified_by_inventory": unclassified_by_inventory,
        }
    )

@router.post("/inventory/add")
async def add_inventory(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    item_code = normalize_item_code(data.get("item_code"))
    warehouse_type = (data.get("warehouse_type") or "").strip()
    category = (data.get("category") or "").strip()
    lot = (data.get("lot") or "").strip()
    grade = (data.get("grade") or "").strip()
    rev = (data.get("rev") or "").strip()
    note = (data.get("note") or "").strip()
    item_name = (data.get("item_name") or "").strip()

    if not item_code:
        return JSONResponse(
            {"status": "error", "message": "품목코드를 입력하세요."},
            status_code=400
        )

    if warehouse_type not in WAREHOUSE_TYPES:
        return JSONResponse(
            {"status": "error", "message": "창고구분을 선택하세요."},
            status_code=400
        )

    if category and category not in CATEGORIES:
        return JSONResponse(
            {"status": "error", "message": "재고구분은 반제품/제품/원자재 중 하나여야 합니다."},
            status_code=400
        )

    try:
        qty = int(data.get("qty") or 0)
    except (TypeError, ValueError):
        return JSONResponse(
            {"status": "error", "message": "수량은 숫자여야 합니다."},
            status_code=400
        )

    if not item_name or not rev or not category:
        auto_name, auto_rev, auto_category = lookup_item_defaults(db, item_code)
        item_name = item_name or auto_name
        rev = rev or auto_rev
        category = category or auto_category

    if category == "원자재":
        lot = ""

    if warehouse_type == "창고재고" and not grade:

        ensure_grade_siblings(db, item_code, warehouse_type, lot, category, item_name, rev)

        db.commit()

        save_log(
            user=current_user(request),
            product=INVENTORY_LOG_PRODUCT,
            action="INVENTORY_ADD",
            serial=item_code,
            detail=f"수불 재고 신규 등록 (A/B/F 자동 생성): {item_name} / {warehouse_type} / LOT {lot or '-'}"
        )

        return JSONResponse({"status": "success", "message": "A/B/F 등급이 모두 생성되었습니다."})

    existing = (
        db.query(Inventory)
        .filter(
            Inventory.item_code == item_code,
            Inventory.warehouse_type == warehouse_type,
            Inventory.lot == lot,
            Inventory.grade == grade,
        )
        .first()
    )

    if existing:
        return JSONResponse(
            {
                "status": "error",
                "message": "이미 동일한 품목코드/창고구분/LOT/등급 조합이 존재합니다."
            },
            status_code=400
        )

    db.add(
        Inventory(
            item_code=item_code,
            item_name=item_name,
            category=category,
            warehouse_type=warehouse_type,
            lot=lot,
            grade=grade,
            rev=rev,
            note=note,
            qty=qty,
        )
    )

    ensure_grade_siblings(db, item_code, warehouse_type, lot, category, item_name, rev)

    db.commit()

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_ADD",
        serial=item_code,
        detail=f"수불 재고 신규 등록: {item_name} / {warehouse_type} / {qty} EA"
    )

    return JSONResponse({"status": "success"})

@router.get("/inventory/mobile/session")
def inventory_mobile_session(request: Request):
    """APK가 저장된 로그인 세션의 유효성을 확인하는 API."""
    return {
        "status": "success",
        "user": current_user(request),
    }


@router.get("/inventory/mobile/items")
def inventory_mobile_items(
    request: Request,
    keyword: str = Query(default="", max_length=100),
    item_code: str = Query(default="", max_length=100),
    lot: str = Query(default="", max_length=100),
    warehouse_type: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """APK에서 OCR 결과에 맞는 수불재고 행을 찾기 위한 JSON API."""
    query = db.query(Inventory)

    normalized_code = normalize_item_code(item_code) if item_code.strip() else ""
    if normalized_code:
        query = query.filter(Inventory.item_code == normalized_code)
    if lot.strip():
        query = query.filter(Inventory.lot == lot.strip())
    if warehouse_type.strip():
        if warehouse_type.strip() not in WAREHOUSE_TYPES:
            return JSONResponse(
                {"status": "error", "message": "올바르지 않은 창고 유형입니다."},
                status_code=400,
            )
        query = query.filter(Inventory.warehouse_type == warehouse_type.strip())
    if keyword.strip():
        term = keyword.strip()
        query = query.filter(
            or_(
                Inventory.item_code.contains(term),
                Inventory.item_name.contains(term),
                Inventory.lot.contains(term),
            )
        )

    items = query.order_by(Inventory.item_code, Inventory.lot, Inventory.id).limit(limit).all()

    return {
        "status": "success",
        "user": current_user(request),
        "items": [
            {
                "id": item.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "category": item.category,
                "warehouse_type": item.warehouse_type,
                "lot": item.lot,
                "grade": item.grade,
                "rev": item.rev,
                "note": item.note,
                "qty": item.qty or 0,
            }
            for item in items
        ],
    }


@router.post("/inventory/lot-register")
async def inventory_lot_register(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    try:
        inventory_id = int(data.get("inventory_id"))
        qty = int(data.get("qty", 0))
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "품목과 수량을 확인하세요."}, status_code=400)

    lot = str(data.get("lot") or "").strip()[:100]
    inspector = str(data.get("inspector") or "").strip()[:100]
    remark = str(data.get("remark") or "").strip()[:500]
    if qty < 0 or not lot:
        return JSONResponse({"status": "error", "message": "LOT를 입력하고 수량은 0 이상으로 입력하세요."}, status_code=400)
    try:
        received_date = parse_first_received_date(str(data.get("first_received_date") or ""))
    except ValueError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)

    item = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if item is None:
        return JSONResponse({"status": "error", "message": "재고 항목을 찾을 수 없습니다."}, status_code=404)
    if item.category != "원자재":
        return JSONResponse({"status": "error", "message": "LOT 입고 등록은 원자재만 가능합니다."}, status_code=400)

    add_to_inventory_lot(db, item, lot, qty, received_date)
    username = current_user(request)
    if qty > 0:
        item.qty = (item.qty or 0) + qty
        db.add(
            InventoryMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                warehouse_type=item.warehouse_type,
                movement_type="IN",
                qty=qty,
                user=username,
                source=remark or "LOT 등록 입고",
                lot=lot,
                inspector=inspector,
                first_received_date=received_date,
            )
        )
    db.commit()
    save_log(
        user=username,
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_MOVE_IN" if qty > 0 else "INVENTORY_LOT_REGISTER",
        serial=item.item_code,
        detail=f"원자재 LOT 등록: {lot} / {qty} EA / 비고: {remark}",
    )
    message = "LOT 정보가 등록되었습니다."
    if qty > 0:
        message = f"LOT {lot}에 {qty} EA를 입고하고 총재고에 반영했습니다."
    return JSONResponse({"status": "success", "message": message})


@router.get("/inventory/{inventory_id}/lots")
def inventory_lots(inventory_id: int, db: Session = Depends(get_db)):
    item = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if item is None:
        return JSONResponse({"status": "error", "message": "재고 항목을 찾을 수 없습니다."}, status_code=404)
    rows = (
        db.query(InventoryLot)
        .filter(InventoryLot.inventory_id == inventory_id, InventoryLot.qty > 0)
        .order_by(InventoryLot.first_received_date, InventoryLot.lot)
        .all()
    )
    return {
        "status": "success",
        "lots": [
            {
                "lot": row.lot,
                "qty": row.qty or 0,
                "first_received_date": row.first_received_date.isoformat() if row.first_received_date else "",
            }
            for row in rows
        ],
        "unclassified_qty": max((item.qty or 0) - tracked_lot_qty(db, item.id), 0),
    }


@router.post("/inventory/move-in")
async def inventory_move_in(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        raw_ids = data.get("ids", [])
        if not isinstance(raw_ids, list):
            raw_ids = [raw_ids]
        ids = list(dict.fromkeys(int(item_id) for item_id in raw_ids))
        qty = int(data.get("qty", 0))
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "재고 항목과 수량을 확인하세요."}, status_code=400)
    if not ids or qty <= 0:
        return JSONResponse({"status": "error", "message": "수량은 1 이상이어야 합니다."}, status_code=400)
    remark = str(data.get("remark") or "").strip()[:500]
    lot = str(data.get("lot") or "").strip()[:100]
    inspector = str(data.get("inspector") or "").strip()[:100]
    try:
        first_received_date = parse_first_received_date(str(data.get("first_received_date") or ""))
    except ValueError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
    username = current_user(request)

    items = db.query(Inventory).filter(Inventory.id.in_(ids)).all()

    found_ids = {item.id for item in items}
    missing_ids = [item_id for item_id in ids if item_id not in found_ids]
    if missing_ids:
        return JSONResponse(
            {
                "status": "error",
                "message": "존재하지 않는 재고 항목이 있습니다.",
                "missing_ids": missing_ids,
            },
            status_code=404,
        )

    for item in items:
        if item.category == "원자재" and lot:
            add_to_inventory_lot(db, item, lot, qty, first_received_date)
        item.qty = (item.qty or 0) + qty

        db.add(
            InventoryMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                warehouse_type=item.warehouse_type,
                movement_type="IN",
                qty=qty,
                user=username,
                source=remark,
                lot=lot,
                inspector=inspector,
                first_received_date=first_received_date,
            )
        )

    db.commit()

    save_log(
        user=username,
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_MOVE_IN",
        serial=summarize_items(items),
        detail=f"수불 재고 입고: {qty} EA / 비고: {remark}"
    )

    return JSONResponse({"status": "success"})

@router.post("/inventory/move-out")
async def inventory_move_out(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        raw_ids = data.get("ids", [])
        if not isinstance(raw_ids, list):
            raw_ids = [raw_ids]
        ids = list(dict.fromkeys(int(item_id) for item_id in raw_ids))
        qty = int(data.get("qty", 0))
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "재고 항목과 수량을 확인하세요."}, status_code=400)
    if not ids or qty <= 0:
        return JSONResponse({"status": "error", "message": "수량은 1 이상이어야 합니다."}, status_code=400)
    remark = str(data.get("remark") or "").strip()[:500]
    lot = str(data.get("lot") or "").strip()[:100]
    inspector = str(data.get("inspector") or "").strip()[:100]
    try:
        first_received_date = parse_first_received_date(str(data.get("first_received_date") or ""))
    except ValueError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
    username = current_user(request)

    items = db.query(Inventory).filter(Inventory.id.in_(ids)).all()

    found_ids = {item.id for item in items}
    missing_ids = [item_id for item_id in ids if item_id not in found_ids]
    if missing_ids:
        return JSONResponse(
            {
                "status": "error",
                "message": "존재하지 않는 재고 항목이 있습니다.",
                "missing_ids": missing_ids,
            },
            status_code=404,
        )

    for item in items:
        if (item.qty or 0) < qty:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"{item.item_code} 재고 부족"
                },
                status_code=400
            )
        if item.category == "원자재":
            if lot:
                lot_row = inventory_lot_row(db, item, lot)
                if lot_row is None:
                    return JSONResponse(
                        {
                            "status": "error",
                            "message": f"등록되지 않은 LOT입니다: {lot}. 먼저 LOT 등록 또는 입고 처리를 해주세요.",
                        },
                        status_code=400,
                    )
                if (lot_row.qty or 0) < qty:
                    return JSONResponse(
                        {"status": "error", "message": f"LOT {lot} 재고 부족 (현재 {lot_row.qty or 0} EA)"},
                        status_code=400,
                    )
            else:
                unclassified = max((item.qty or 0) - tracked_lot_qty(db, item.id), 0)
                if unclassified < qty:
                    return JSONResponse(
                        {"status": "error", "message": f"미분류 기초재고 부족 (현재 {unclassified} EA)"},
                        status_code=400,
                    )

    for item in items:
        if item.category == "원자재" and lot:
            lot_row = inventory_lot_row(db, item, lot)
            lot_row.qty -= qty
        item.qty -= qty

        db.add(
            InventoryMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                warehouse_type=item.warehouse_type,
                movement_type="OUT",
                qty=qty,
                user=username,
                source=remark,
                lot=lot,
                inspector=inspector,
                first_received_date=first_received_date,
            )
        )

    db.commit()

    save_log(
        user=username,
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_MOVE_OUT",
        serial=summarize_items(items),
        detail=f"수불 재고 출고: {qty} EA / 비고: {remark}"
    )

    return JSONResponse({"status": "success"})

@router.post("/inventory/delete-selected")
async def delete_selected_inventory(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])

    items = db.query(Inventory).filter(Inventory.id.in_(ids)).all()

    for item in items:
        db.query(InventoryLot).filter(InventoryLot.inventory_id == item.id).delete()
        db.delete(item)

    db.commit()

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_DELETE_SELECTED",
        serial=summarize_items(items),
        detail=f"수불 재고 선택 삭제: {len(items)}건"
    )

    return JSONResponse({"status": "success"})

@router.post("/inventory/update-field")
async def update_inventory_field(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    item = db.query(Inventory).filter(Inventory.id == data.get("id")).first()

    if not item:
        return JSONResponse({"status": "error"}, status_code=404)

    field = data.get("field")

    if field not in ("qty", "lot", "note"):
        return JSONResponse({"status": "error", "message": "잘못된 필드입니다."}, status_code=400)

    value = data.get("value", "")
    old_value = getattr(item, field)

    if field == "lot" and item.category == "원자재" and value.strip():
        return JSONResponse(
            {"status": "error", "message": "원자재는 LOT을 사용하지 않습니다."},
            status_code=400
        )

    if field == "qty":
        try:
            value = int(value)
        except (TypeError, ValueError):
            return JSONResponse({"status": "error", "message": "숫자만 입력 가능합니다."}, status_code=400)

        db.add(
            InventoryMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                warehouse_type=item.warehouse_type,
                movement_type="ADJUST",
                qty=value - (old_value or 0),
                user=current_user(request),
                source="manual_edit"
            )
        )

    setattr(item, field, value)

    db.commit()

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_UPDATE_FIELD",
        serial=item.item_code,
        detail=f"{field} 변경: {old_value or '-'} -> {value or '-'}"
    )

    return JSONResponse({"status": "success"})

@router.post("/inventory/bulk-update-qty")
async def bulk_update_inventory_qty(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])

    try:
        qty = int(data.get("qty"))
    except (TypeError, ValueError):
        return JSONResponse(
            {"status": "error", "message": "숫자만 입력 가능합니다."},
            status_code=400
        )

    items = db.query(Inventory).filter(Inventory.id.in_(ids)).all()

    for item in items:

        old_qty = item.qty or 0
        item.qty = qty

        db.add(
            InventoryMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                warehouse_type=item.warehouse_type,
                movement_type="ADJUST",
                qty=qty - old_qty,
                user=current_user(request),
                source="bulk_edit"
            )
        )

    db.commit()

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_BULK_UPDATE_QTY",
        serial=summarize_items(items),
        detail=f"수불 재고 수량 일괄 변경: {len(items)}건 -> {qty} EA"
    )

    return JSONResponse({"status": "success"})

@router.post("/inventory/bulk-update-note")
async def bulk_update_inventory_note(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])
    note = data.get("note", "")

    items = db.query(Inventory).filter(Inventory.id.in_(ids)).all()

    for item in items:
        item.note = note

    db.commit()

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_BULK_UPDATE_NOTE",
        serial=summarize_items(items),
        detail=f"수불 재고 비고 일괄 변경: {len(items)}건 -> {note}"
    )

    return JSONResponse({"status": "success"})

@router.post("/inventory/bulk-update-lot")
async def bulk_update_inventory_lot(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])
    lot = (data.get("lot") or "").strip()
    items = db.query(Inventory).filter(Inventory.id.in_(ids)).all()
    applied = [item for item in items if item.category != "원자재"]
    skipped = len(items) - len(applied)

    for item in applied:
        item.lot = lot

    db.commit()

    message = f"LOT 일괄 변경: {len(applied)}건"

    if skipped:
        message += f" / 원자재 제외 {skipped}건"

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_BULK_UPDATE_LOT",
        serial=summarize_items(applied),
        detail=f"{message} -> {lot or '-'}"
    )

    return JSONResponse({"status": "success", "applied": len(applied), "skipped": skipped, "message": message})

@router.get("/inventory/history")
def inventory_history(
    request: Request,
    movement_type: str = "IN",
    page: int = 1,
    keyword: str = "",
    category: str = "",
    db: Session = Depends(get_db)
):
    per_page = 50

    query = db.query(InventoryMovement).filter(
        InventoryMovement.movement_type == movement_type
    )

    if keyword:
        query = query.filter(
            or_(
                InventoryMovement.item_code.contains(keyword),
                InventoryMovement.item_name.contains(keyword),
                InventoryMovement.user.contains(keyword),
                InventoryMovement.lot.contains(keyword),
                InventoryMovement.inspector.contains(keyword),
            )
        )

    category_values = filter_values(request, "category")
    if category_values:
        query = query.filter(InventoryMovement.category.in_(category_values))

    query = query.order_by(InventoryMovement.created_at.desc())

    total_count = query.count()

    history = (
        query
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_pages = max(1, ceil(total_count / per_page))

    return templates.TemplateResponse(
        request=request,
        name="inventory/history.html",
        context={
            "history": history,
            "page": page,
            "total_pages": total_pages,
            "movement_type": movement_type,
            "keyword": keyword,
            "category": category,
            "format_kst": format_kst,
        }
    )

@router.get("/inventory/history/download-excel")
def download_inventory_history_excel(
    request: Request,
    db: Session = Depends(get_db)
):

    history = (
        db.query(InventoryMovement)
        .order_by(InventoryMovement.created_at.desc())
        .all()
    )

    data = [
        {
            "일시": format_kst(row.created_at),
            "품목코드": row.item_code,
            "품명": row.item_name,
            "구분": row.category,
            "창고구분": row.warehouse_type,
            "유형": "입고" if row.movement_type == "IN" else "출고",
            "수량": row.qty,
            "LOT": row.lot or "",
            "검사원": row.inspector or "",
            "최초 입고일자": row.first_received_date.strftime("%Y-%m-%d") if row.first_received_date else "",
            "작업자": row.user,
            "비고": row.source
        }
        for row in history
    ]

    df = pd.DataFrame(data)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="History")

    output.seek(0)

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_HISTORY_DOWNLOAD_EXCEL",
        detail=f"수불 재고 입출고 이력 다운로드: {len(history)}건"
    )

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": download_content_disposition(
            "수불 재고 입출고 이력", "inventory_history"
        )}
    )

@router.get("/inventory/dashboard")
def inventory_dashboard(
    request: Request,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db)
):

    warehouse_filter = Inventory.warehouse_type == "창고재고"
    movement_filter = InventoryMovement.warehouse_type == "창고재고"

    total_items = (
        db.query(func.count(distinct(Inventory.item_code)))
        .filter(warehouse_filter)
        .scalar()
    )

    total_qty = (
        db.query(func.coalesce(func.sum(Inventory.qty), 0))
        .filter(warehouse_filter)
        .scalar()
    )

    today_in = (
        db.query(func.coalesce(func.sum(InventoryMovement.qty), 0))
        .filter(InventoryMovement.movement_type == "IN", movement_filter)
        .scalar()
    )

    today_out = (
        db.query(func.coalesce(func.sum(InventoryMovement.qty), 0))
        .filter(InventoryMovement.movement_type == "OUT", movement_filter)
        .scalar()
    )

    category_labels = []
    category_qtys = []

    for category in CATEGORIES:

        qty = (
            db.query(func.coalesce(func.sum(Inventory.qty), 0))
            .filter(warehouse_filter, Inventory.category == category)
            .scalar()
        )

        category_labels.append(category)
        category_qtys.append(qty)

    semi_data = {
        "RING": 0,
        "CRADLE": 0
    }

    semi_items = (
        db.query(Inventory)
        .filter(warehouse_filter, Inventory.category == "반제품")
        .all()
    )

    for item in semi_items:

        sub = get_sub_category(item.item_name)

        if sub in semi_data:
            semi_data[sub] += item.qty or 0

    raw_data = {
        "INNER": 0,
        "OUTER": 0,
        "TOP COVER": 0,
        "PBA": 0,
        "사급자재": 0
    }

    raw_items = (
        db.query(Inventory)
        .filter(warehouse_filter, Inventory.category == "원자재")
        .all()
    )

    for item in raw_items:

        sub = get_raw_category(item.item_name)
        raw_data[sub] += item.qty or 0

    movement_chart = {
        "반제품": {"IN": 0, "OUT": 0},
        "제품": {"IN": 0, "OUT": 0},
        "원자재": {"IN": 0, "OUT": 0}
    }

    movement_query = db.query(InventoryMovement).filter(movement_filter)

    if start and end:

        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")

        movement_query = movement_query.filter(
            InventoryMovement.created_at >= start_date,
            InventoryMovement.created_at <= end_date
        )

    for move in movement_query.all():

        category = move.category
        movement_type = move.movement_type

        if category in movement_chart and movement_type in ("IN", "OUT"):
            movement_chart[category][movement_type] += move.qty or 0

    return templates.TemplateResponse(
        request=request,
        name="inventory/dashboard.html",
        context={
            "total_items": total_items,
            "total_qty": total_qty,
            "today_in": today_in,
            "today_out": today_out,
            "start": start,
            "end": end,
            "category_labels": category_labels,
            "category_qtys": category_qtys,
            "semi_labels": list(semi_data.keys()),
            "semi_qtys": list(semi_data.values()),
            "raw_labels": list(raw_data.keys()),
            "raw_qtys": list(raw_data.values()),
            "movement_labels": ["반제품", "제품", "원자재"],
            "movement_in": [
                movement_chart["반제품"]["IN"],
                movement_chart["제품"]["IN"],
                movement_chart["원자재"]["IN"]
            ],
            "movement_out": [
                movement_chart["반제품"]["OUT"],
                movement_chart["제품"]["OUT"],
                movement_chart["원자재"]["OUT"]
            ]
        }
    )

@router.get("/inventory/download")
def download_inventory_excel(request: Request, db: Session = Depends(get_db)):

    rows = (
        db.query(Inventory)
        .order_by(Inventory.item_code, Inventory.warehouse_type)
        .all()
    )

    data = [
        {
            "품목코드": row.item_code,
            "품명": row.item_name,
            "구분": row.category,
            "창고구분": row.warehouse_type,
            "LOT": row.lot,
            "Grade": row.grade,
            "Rev": row.rev,
            "수량": row.qty,
            "비고": row.note
        }
        for row in rows
    ]

    df = pd.DataFrame(data)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory")

    output.seek(0)

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_DOWNLOAD_EXCEL",
        detail=f"수불 재고 엑셀 다운로드: {len(rows)}건"
    )

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": download_content_disposition(
            "수불 재고 현황", "inventory"
        )}
    )

@router.post("/inventory/init-excel")
async def init_inventory_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    created = 0
    skipped = 0

    required = ["품목코드", "창고구분"]

    for col in required:
        if col not in df.columns:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"{col} 컬럼이 없습니다."
                },
                status_code=400
            )

    has_category_col = "구분" in df.columns
    has_lot_col = "LOT" in df.columns
    has_note_col = "비고" in df.columns

    for _, row in df.iterrows():

        item_code = normalize_item_code(
            row["품목코드"]
        )

        warehouse_type = str(
            row["창고구분"]
        ).strip()

        lot = (
            str(row["LOT"]).strip()
            if has_lot_col and pd.notna(row["LOT"])
            else ""
        )

        note = (
            str(row["비고"]).strip()
            if has_note_col and pd.notna(row["비고"])
            else ""
        )

        given_category = (
            str(row["구분"]).strip()
            if has_category_col and pd.notna(row["구분"])
            else ""
        )

        item_name, rev, auto_category = lookup_item_defaults(
            db,
            item_code
        )

        if not item_name:
            skipped += 1
            continue

        category = (
            given_category
            if given_category in CATEGORIES
            else auto_category
        )

        if category == "원자재":
            lot = ""

        if warehouse_type == "창고재고":

            for grade in GRADES:

                exists = (
                    db.query(Inventory)
                    .filter(
                        Inventory.item_code == item_code,
                        Inventory.warehouse_type == warehouse_type,
                        Inventory.lot == lot,
                        Inventory.grade == grade
                    )
                    .first()
                )

                if exists:
                    continue

                db.add(
                    Inventory(
                        item_code=item_code,
                        item_name=item_name,
                        category=category,
                        warehouse_type=warehouse_type,
                        lot=lot,
                        grade=grade,
                        rev=rev,
                        note=note,
                        qty=0
                    )
                )

                created += 1

        else:

            exists = (
                db.query(Inventory)
                .filter(
                    Inventory.item_code == item_code,
                    Inventory.warehouse_type == warehouse_type
                )
                .first()
            )

            if exists:
                continue

            db.add(
                Inventory(
                    item_code=item_code,
                    item_name=item_name,
                    category=category,
                    warehouse_type=warehouse_type,
                    lot="",
                    grade="",
                    rev=rev,
                    note=note,
                    qty=0
                )
            )

            created += 1

    db.commit()

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_INIT_EXCEL",
        detail=(
            f"수불 재고 초기 생성 "
            f"(신규 {created}건 / 제외 {skipped}건)"
        )
    )

    return JSONResponse(
        {
            "status": "success",
            "created": created,
            "skipped": skipped,
            "message":
                f"신규 {created}건 / 제외 {skipped}건"
        }
    )

@router.post("/inventory/upload")
async def upload_inventory_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    required = ["품목코드", "창고구분"]

    for col in required:
        if col not in df.columns:
            return JSONResponse(
                {"status": "error", "message": f"{col} 컬럼이 없습니다."},
                status_code=400
            )

    created = 0
    updated = 0
    skipped = 0

    has_note_col = "비고" in df.columns
    has_category_col = "구분" in df.columns
    has_lot_col = "LOT" in df.columns
    has_grade_col = "Grade" in df.columns
    has_qty_col = "수량" in df.columns

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):

        item_code = normalize_item_code(
            row["품목코드"]
        )
        warehouse_type = str(row["창고구분"]).strip()

        lot = (
            str(row["LOT"]).strip()
            if has_lot_col and pd.notna(row["LOT"])
            else ""
        )

        grade = (
            str(row["Grade"]).strip()
            if has_grade_col and pd.notna(row["Grade"])
            else ""
        )

        try:
            qty = parse_excel_quantity(row["수량"]) if has_qty_col else 0
        except ValueError:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"엑셀 {row_number}행의 수량 값이 올바르지 않습니다: {row['수량']}"
                },
                status_code=400
            )

        note = (
            str(row["비고"]).strip()
            if has_note_col and pd.notna(row["비고"])
            else ""
        )

        given_category = (
            str(row["구분"]).strip()
            if has_category_col and pd.notna(row["구분"])
            else ""
        )

        item_name, rev, auto_category = lookup_item_defaults(db, item_code)

        if not item_name:

            skipped += 1
            continue

        category = given_category if given_category in CATEGORIES else auto_category

        if category == "원자재":
            lot = ""

        if warehouse_type == "창고재고" and not grade:
            ensure_grade_siblings(db, item_code, warehouse_type, lot, category, item_name, rev)
            created += 1
            continue

        existing = (
            db.query(Inventory)
            .filter(
                Inventory.item_code == item_code,
                Inventory.warehouse_type == warehouse_type,
                Inventory.lot == lot,
                Inventory.grade == grade
            )
            .first()
        )

        if existing:

            existing.item_name = item_name
            existing.category = category
            existing.rev = rev
            existing.note = note
            existing.qty = qty

            updated += 1

        else:
            db.add(
                Inventory(
                    item_code=item_code,
                    item_name=item_name,
                    category=category,
                    warehouse_type=warehouse_type,
                    lot=lot,
                    grade=grade,
                    rev=rev,
                    note=note,
                    qty=qty
                )
            )

            created += 1

        ensure_grade_siblings(db, item_code, warehouse_type, lot, category, item_name, rev)

    db.commit()

    message = (
        f"신규 {created}건 "
        f"/ 수정 {updated}건 "
        f"/ 제외 {skipped}건"
    )

    save_log(
        user=current_user(request),
        product=INVENTORY_LOG_PRODUCT,
        action="INVENTORY_UPLOAD_EXCEL",
        detail=f"수불 재고 업로드: {message}"
    )

    return JSONResponse(
    {
        "status":"success",
        "created":created,
        "updated":updated,
        "skipped":skipped,
        "message":message
    }
    )

@router.get("/mrp/inventory")
def redirect_old_inventory_page():
    return RedirectResponse("/inventory", status_code=307)
