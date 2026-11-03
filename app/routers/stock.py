from app.utils.filters import filter_values
from fastapi import (
    APIRouter,
    Request,
    Depends,
    Body
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
    FileResponse
)
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.stock import Stock
from app.models.stock_movement import StockMovement
from app.models.stock_lot import StockLot
import pandas as pd
from io import BytesIO
from app.models.item_master import ItemMaster
from app.models.item_master_history import ItemMasterHistory
from fastapi import UploadFile, File
import tempfile
from math import ceil
from sqlalchemy import or_, func
from app.models.bom import BOM
from app.models.inventory import Inventory
from app.models.material_master import MaterialMaster
from app.models.material_note import MaterialNote
from app.utils.logger import save_log
from app.utils.downloads import dated_filename, download_content_disposition
from app.utils.item_codes import normalize_item_code
from app.utils.timezone import format_kst
from app.utils.timezone import utc_now_naive
from datetime import datetime, timedelta
from uuid import uuid4

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

STOCK_LOG_PRODUCT = "가계상 재고"

def current_user(request: Request):
    return request.session.get("user") or "system"

def summarize_items(items):
    codes = [
        item.item_code
        for item in items[:10]
    ]

    suffix = (
        f" 외 {len(items) - 10}건"
        if len(items) > 10
        else ""
    )

    return ", ".join(codes) + suffix

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def parse_stock_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("최초 입고일자는 YYYY-MM-DD 형식으로 입력하세요.") from exc


def stock_lot_row(db, item, lot):
    if not lot:
        return None
    return db.query(StockLot).filter(StockLot.stock_id == item.id, StockLot.lot == lot).first()


@router.get("/stock/mobile/items")
def stock_mobile_items(
    request: Request,
    keyword: str = "",
    item_code: str = "",
    lot: str = "",
    grade: str = "",
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Stock)
    normalized_code = normalize_item_code(item_code) if item_code.strip() else ""
    if normalized_code:
        query = query.filter(Stock.item_code == normalized_code)
    if grade.strip():
        query = query.filter(Stock.grade == grade.strip().upper())
    if keyword.strip():
        term = keyword.strip()
        query = query.filter(or_(Stock.item_code.contains(term), Stock.item_name.contains(term)))
    items = query.order_by(Stock.item_code, Stock.grade, Stock.id).limit(max(1, min(limit, 100))).all()
    return {
        "status": "success",
        "user": current_user(request),
        "items": [
            {
                "id": item.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "category": item.category,
                "warehouse_type": "가계상 재고",
                "lot": "",
                "grade": item.grade or "",
                "rev": item.rev or "",
                "qty": item.qty or 0,
                "requested_lot": lot.strip(),
                "lot_qty": ((stock_lot_row(db, item, lot.strip()).qty or 0) if stock_lot_row(db, item, lot.strip()) else 0),
            }
            for item in items
        ],
    }


@router.get("/stock/mobile/history")
def stock_mobile_history(request: Request, limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(StockMovement)
        .filter(StockMovement.user == current_user(request))
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return {
        "status": "success",
        "items": [
            {
                "id": row.id,
                "item_code": row.item_code or "",
                "item_name": row.item_name or "",
                "warehouse_type": "가계상 재고",
                "movement_type": row.movement_type or "",
                "qty": row.qty or 0,
                "lot": row.lot or "",
                "inspector": row.inspector or "",
                "source": row.source or "",
                "grade": row.grade or "",
                "request_id": row.request_id or "",
                "set_name": row.set_name or "",
                "set_component": row.set_component or "",
                "set_count": row.set_count or 0,
                "created_at": format_kst(row.created_at),
            }
            for row in rows
        ],
    }


@router.post("/stock/mobile/duplicate-check")
async def stock_mobile_duplicate_check(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    try:
        stock_id, qty = int(data.get("inventory_id")), int(data.get("qty"))
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "품목과 수량을 확인하세요."}, status_code=400)
    item = db.query(Stock).filter(Stock.id == stock_id).first()
    if item is None:
        return JSONResponse({"status": "error", "message": "재고 항목을 찾을 수 없습니다."}, status_code=404)
    movement_type = str(data.get("movement_type") or "").upper()
    lot = str(data.get("lot") or "").strip()
    duplicate = db.query(StockMovement).filter(
        StockMovement.user == current_user(request),
        StockMovement.item_code == item.item_code,
        StockMovement.movement_type == movement_type,
        StockMovement.qty == qty,
        StockMovement.lot == lot,
        StockMovement.created_at >= utc_now_naive() - timedelta(minutes=3),
    ).order_by(StockMovement.created_at.desc()).first()
    return {"status": "success", "duplicate": duplicate is not None, "previous_at": format_kst(duplicate.created_at) if duplicate else ""}


async def stock_mobile_move_common(request, data, inbound, db):
    try:
        stock_id, qty = int(data.get("inventory_id")), int(data.get("qty"))
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "품목과 수량을 확인하세요."}, status_code=400)
    if qty <= 0:
        return JSONResponse({"status": "error", "message": "수량은 1 이상이어야 합니다."}, status_code=400)
    item = db.query(Stock).filter(Stock.id == stock_id).first()
    if item is None:
        return JSONResponse({"status": "error", "message": "재고 항목을 찾을 수 없습니다."}, status_code=404)
    lot = str(data.get("lot") or "").strip()[:100]
    inspector = str(data.get("inspector") or "").strip()[:100]
    remark = str(data.get("remark") or "").strip()[:500]
    try:
        received_date = parse_stock_date(str(data.get("first_received_date") or ""))
    except ValueError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
    lot_row = stock_lot_row(db, item, lot)
    before_qty, lot_before = item.qty or 0, (lot_row.qty or 0) if lot_row else 0
    if not inbound and before_qty < qty:
        return JSONResponse({"status": "error", "message": f"{item.item_code} 재고가 부족합니다."}, status_code=400)
    if not inbound and lot and (lot_row is None or lot_before < qty):
        return JSONResponse({"status": "error", "message": f"LOT {lot} 재고 부족 (현재 {lot_before} EA)"}, status_code=400)
    if lot and lot_row is None:
        lot_row = StockLot(stock_id=item.id, item_code=item.item_code, grade=item.grade, lot=lot, qty=0)
        db.add(lot_row)
    if lot_row is not None:
        lot_row.qty = (lot_row.qty or 0) + qty if inbound else (lot_row.qty or 0) - qty
        if received_date and not lot_row.first_received_date:
            lot_row.first_received_date = received_date
        if inspector:
            lot_row.inspector = inspector
    item.qty = before_qty + qty if inbound else before_qty - qty
    db.add(StockMovement(
        item_code=item.item_code, item_name=item.item_name, category=item.category,
        movement_type="IN" if inbound else "OUT", qty=qty, user=current_user(request), source=remark,
        lot=lot, inspector=inspector, first_received_date=received_date, grade=item.grade,
    ))
    db.commit()
    return {"status": "success", "results": [{"inventory_id": item.id, "before_qty": before_qty, "after_qty": item.qty or 0, "lot": lot, "lot_before_qty": lot_before, "lot_after_qty": lot_row.qty if lot_row else 0}]}


@router.post("/stock/mobile/move-in")
async def stock_mobile_move_in(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return await stock_mobile_move_common(request, data, True, db)


@router.post("/stock/mobile/move-out")
async def stock_mobile_move_out(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return await stock_mobile_move_common(request, data, False, db)


@router.post("/stock/mobile/lot-register")
async def stock_mobile_lot_register(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    data = dict(data)
    raw_qty = data.get("qty", 0)
    try:
        qty = 0 if raw_qty in (None, "") else int(raw_qty)
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "수량을 확인하세요."}, status_code=400)
    if qty < 0 or not str(data.get("lot") or "").strip():
        return JSONResponse({"status": "error", "message": "LOT를 입력하고 수량은 0 이상으로 입력하세요."}, status_code=400)
    if qty == 0:
        try:
            item = db.query(Stock).filter(Stock.id == int(data.get("inventory_id"))).first()
        except (TypeError, ValueError):
            item = None
        if item is None:
            return JSONResponse({"status": "error", "message": "재고 항목을 찾을 수 없습니다."}, status_code=404)
        if item.category != "원자재":
            return JSONResponse({"status": "error", "message": "LOT 등록은 원자재 품목만 가능합니다."}, status_code=400)
        lot = str(data.get("lot") or "").strip()[:100]
        row = stock_lot_row(db, item, lot)
        if row is None:
            row = StockLot(stock_id=item.id, item_code=item.item_code, grade=item.grade, lot=lot, qty=0)
            db.add(row)
        row.inspector = str(data.get("inspector") or "").strip()[:100]
        try:
            row.first_received_date = parse_stock_date(str(data.get("first_received_date") or ""))
        except ValueError as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
        db.commit()
        return {"status": "success", "results": [{"inventory_id": item.id, "before_qty": item.qty or 0, "after_qty": item.qty or 0, "lot": lot, "lot_before_qty": 0, "lot_after_qty": row.qty or 0}]}
    return await stock_mobile_move_common(request, data, True, db)


@router.post("/stock/lot-register")
async def stock_lot_register(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """웹과 APK가 동일한 가계상 LOT 등록 규칙을 사용한다."""
    return await stock_mobile_lot_register(request, data, db)


@router.get("/stock/{stock_id}/lots")
def stock_lots(stock_id: int, db: Session = Depends(get_db)):
    item = db.query(Stock).filter(Stock.id == stock_id).first()
    if item is None:
        return JSONResponse({"status": "error", "message": "재고 항목을 찾을 수 없습니다."}, status_code=404)
    rows = db.query(StockLot).filter(StockLot.stock_id == stock_id).order_by(StockLot.first_received_date, StockLot.lot).all()
    tracked_qty = sum(row.qty or 0 for row in rows)
    return {
        "status": "success",
        "lots": [
            {
                "lot": row.lot,
                "qty": row.qty or 0,
                "grade": row.grade or item.grade or "",
                "inspector": row.inspector or "",
                "first_received_date": row.first_received_date.isoformat() if row.first_received_date else "",
            }
            for row in rows
        ],
        "unclassified_qty": max((item.qty or 0) - tracked_qty, 0),
    }


@router.post("/stock/mobile/set-move-out")
async def stock_mobile_set_move_out(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    lines = data.get("lines")
    try:
        target_sets = int(data.get("target_sets", 0))
    except (TypeError, ValueError):
        target_sets = 0
    if not isinstance(lines, list) or not lines or target_sets <= 0:
        return JSONResponse({"status": "error", "message": "세트 출고 품목과 수량을 확인하세요."}, status_code=400)
    component_types = {"PBA", "OUTER", "INNER", "TOP_COVER"}
    parsed, totals, item_totals = [], {key: 0 for key in component_types}, {}
    try:
        for raw in lines:
            stock_id, qty = int(raw.get("inventory_id")), int(raw.get("qty"))
            component, lot = str(raw.get("component") or "").upper(), str(raw.get("lot") or "").strip()
            if stock_id <= 0 or qty <= 0 or component not in component_types or not lot:
                raise ValueError
            parsed.append((stock_id, lot, qty, component))
            totals[component] += qty
            item_totals[stock_id] = item_totals.get(stock_id, 0) + qty
    except (AttributeError, TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "세트 출고의 품목·LOT·수량을 확인하세요."}, status_code=400)
    if any(value != target_sets for value in totals.values()):
        return JSONResponse({"status": "error", "message": "모든 구성품 수량이 세트 수량과 같아야 합니다."}, status_code=400)
    items = {row.id: row for row in db.query(Stock).filter(Stock.id.in_(item_totals)).all()}
    if len(items) != len(item_totals):
        return JSONResponse({"status": "error", "message": "존재하지 않는 품목이 포함되어 있습니다."}, status_code=404)
    lot_rows = {}
    for stock_id, lot, qty, _ in parsed:
        item, row = items[stock_id], stock_lot_row(db, items[stock_id], lot)
        if (item.qty or 0) < item_totals[stock_id] or row is None or (row.qty or 0) < qty:
            return JSONResponse({"status": "error", "message": f"{item.item_code} / LOT {lot} 재고가 부족합니다."}, status_code=400)
        lot_rows[(stock_id, lot)] = row
    request_id = str(data.get("request_id") or uuid4())[:100]
    if db.query(StockMovement).filter(StockMovement.user == current_user(request), StockMovement.request_id == request_id).first():
        return JSONResponse({"status": "error", "message": "이미 처리된 세트 출고 요청입니다."}, status_code=409)
    results = []
    for stock_id, lot, qty, component in parsed:
        item, row = items[stock_id], lot_rows[(stock_id, lot)]
        before, lot_before = item.qty or 0, row.qty or 0
        item.qty -= qty
        row.qty -= qty
        db.add(StockMovement(
            item_code=item.item_code, item_name=item.item_name, category=item.category, movement_type="OUT",
            qty=qty, user=current_user(request), source=str(data.get("remark") or "")[:500], grade=item.grade,
            lot=lot, request_id=request_id, set_name=str(data.get("set_name") or "세트 출고")[:100],
            set_component=component, set_count=target_sets,
        ))
        results.append({"inventory_id": item.id, "component": component, "item_code": item.item_code, "lot": lot, "qty": qty, "before_qty": before, "after_qty": item.qty or 0, "lot_before_qty": lot_before, "lot_after_qty": row.qty or 0})
    db.commit()
    return {"status": "success", "group_id": request_id, "set_name": str(data.get("set_name") or "세트 출고"), "target_sets": target_sets, "results": results}

@router.get("/stock")
def inventory_dashboard(
    request: Request,
    category: str = "반제품",
    page: int = 1,
    keyword: str = "",
    grade: str = "",
    rev: str = "",
    db: Session = Depends(get_db)
):
    per_page = 50

    query = (
        db.query(Stock)
        .filter(
            Stock.category == category
        )
    )

    if keyword:

        query = query.filter(
            or_(
                Stock.item_code.contains(keyword),
                Stock.item_name.contains(keyword)
            )
        )

    scoped_rows = query.all()

    revs = sorted(
        {row.rev for row in scoped_rows if row.rev} | {"COMMON"}
    )

    grade_values = filter_values(request, "grade")
    if grade_values:
        query = query.filter(Stock.grade.in_(grade_values))

    rev_values = filter_values(request, "rev")
    if rev_values:
        query = query.filter(Stock.rev.in_(rev_values))

    total_count = query.count()

    items = (
        query
        .order_by(
            Stock.item_code,
            Stock.grade
        )
        .offset(
            (page - 1) * per_page
        )
        .limit(per_page)
        .all()
    )

    lot_details_by_stock = {}
    unclassified_by_stock = {}
    if category == "원자재" and items:
        item_ids = [item.id for item in items]
        lot_rows = (
            db.query(StockLot)
            .filter(StockLot.stock_id.in_(item_ids))
            .order_by(StockLot.first_received_date, StockLot.lot)
            .all()
        )
        for row in lot_rows:
            lot_details_by_stock.setdefault(row.stock_id, []).append(row)
        for item in items:
            tracked = sum(row.qty or 0 for row in lot_details_by_stock.get(item.id, []))
            unclassified_by_stock[item.id] = max((item.qty or 0) - tracked, 0)

    total_pages = max(
        1,
        ceil(total_count / per_page)
    )

    category_totals = dict(
        db.query(Stock.category, func.sum(Stock.qty))
        .group_by(Stock.category)
        .all()
    )

    semi_qty = category_totals.get("반제품", 0) or 0
    product_qty = category_totals.get("제품", 0) or 0
    raw_qty = category_totals.get("원자재", 0) or 0

    return templates.TemplateResponse(
        request=request,
        name="stock/index.html",
        context={
            "items": items,
            "current_category": category,
            "page": page,
            "keyword": keyword,
            "current_grade": grade,
            "current_rev": rev,
            "revs": revs,
            "total_pages": total_pages,
            "semi_qty": semi_qty,
            "product_qty": product_qty,
            "raw_qty": raw_qty,
            "lot_details_by_stock": lot_details_by_stock,
            "unclassified_by_stock": unclassified_by_stock,
        }
    )

@router.post("/stock/move-in")
async def stock_move_in(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])
    qty = int(data.get("qty", 0))
    if not ids or qty <= 0:
        return JSONResponse({"status": "error", "message": "품목을 선택하고 수량은 1 이상으로 입력하세요."}, status_code=400)

    lot = str(data.get("lot") or "").strip()
    if lot:
        if len(ids) != 1:
            return JSONResponse({"status": "error", "message": "LOT 입고는 품목을 한 개만 선택하세요."}, status_code=400)
        payload = dict(data)
        payload["inventory_id"] = ids[0]
        return await stock_mobile_move_common(request, payload, True, db)

    remark = data.get(
        "remark",
        ""
    )

    username = (
        request.session.get("user")
        or "system"
    )

    items = (
        db.query(Stock)
        .filter(
            Stock.id.in_(ids)
        )
        .all()
    )

    for item in items:

        item.qty += qty

        db.add(
            StockMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                movement_type="IN",
                qty=qty,
                user=username,
                source=remark,
                grade=item.grade,
            )
        )

    db.commit()

    save_log(
        user=username,
        product=STOCK_LOG_PRODUCT,
        action="STOCK_MOVE_IN",
        serial=summarize_items(items),
        detail=f"가계상 재고 입고: {qty} EA / 비고: {remark}"
    )

    return JSONResponse(
        {
            "status": "success"
        }
    )

@router.post("/stock/move-out")
async def stock_move_out(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])
    qty = int(data.get("qty", 0))
    if not ids or qty <= 0:
        return JSONResponse({"status": "error", "message": "품목을 선택하고 수량은 1 이상으로 입력하세요."}, status_code=400)

    lot = str(data.get("lot") or "").strip()
    if lot:
        if len(ids) != 1:
            return JSONResponse({"status": "error", "message": "LOT 출고는 품목을 한 개만 선택하세요."}, status_code=400)
        payload = dict(data)
        payload["inventory_id"] = ids[0]
        return await stock_mobile_move_common(request, payload, False, db)

    remark = data.get(
        "remark",
        ""
    )

    username = (
        request.session.get("user")
        or "system"
    )

    items = (
        db.query(Stock)
        .filter(
            Stock.id.in_(ids)
        )
        .all()
    )

    for item in items:

        if item.qty < qty:

            return JSONResponse(
                {
                    "status": "error",
                    "message":
                    f"{item.item_code} 재고 부족"
                },
                status_code=400
            )
        if item.category == "원자재":
            tracked = db.query(func.coalesce(func.sum(StockLot.qty), 0)).filter(StockLot.stock_id == item.id).scalar() or 0
            unclassified = max((item.qty or 0) - tracked, 0)
            if unclassified < qty:
                return JSONResponse(
                    {"status": "error", "message": f"{item.item_code} 미분류 재고 부족 (현재 {unclassified} EA). 출고 LOT를 선택하세요."},
                    status_code=400,
                )

    for item in items:

        item.qty -= qty

        db.add(
            StockMovement(
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                movement_type="OUT",
                qty=qty,
                user=username,
                source=remark,
                grade=item.grade,
            )
        )

    db.commit()

    save_log(
        user=username,
        product=STOCK_LOG_PRODUCT,
        action="STOCK_MOVE_OUT",
        serial=summarize_items(items),
        detail=f"가계상 재고 출고: {qty} EA / 비고: {remark}"
    )

    return JSONResponse(
        {
            "status": "success"
        }
    )

@router.post("/stock/delete-selected")
async def delete_selected_stock(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data.get("ids", [])

    items = (
        db.query(Stock)
        .filter(
            Stock.id.in_(ids)
        )
        .all()
    )

    for item in items:
        db.delete(item)

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_DELETE_SELECTED",
        serial=summarize_items(items),
        detail=f"가계상 재고 선택 삭제: {len(items)}건"
    )

    return JSONResponse(
        {
            "status": "success"
        }
    )

@router.get("/stock/history")
def stock_history(
    request: Request,
    movement_type: str = "",
    page: int = 1,
    keyword: str = "",
    category: str = "",
    db: Session = Depends(get_db)
):
    per_page = 50

    query = db.query(StockMovement)
    if movement_type in {"IN", "OUT"}:
        query = query.filter(StockMovement.movement_type == movement_type)

    if keyword:

        query = query.filter(

            or_(

                StockMovement.item_code.contains(
                    keyword
                ),

                StockMovement.item_name.contains(
                    keyword
                ),

                StockMovement.user.contains(
                    keyword
                )

            )

        )

    category_values = filter_values(request, "category")
    if category_values:
        query = query.filter(StockMovement.category.in_(category_values))

    all_rows = query.order_by(StockMovement.created_at.desc()).all()
    total_count = len(all_rows)
    history = all_rows[(page - 1) * per_page: page * per_page]

    total_pages = max(
        1,
        ceil(total_count / per_page)
    )

    return templates.TemplateResponse(
        request=request,
        name="stock/history.html",
        context={
            "history": history,
            "total_count": total_count,
            "summary": {
                "inbound": sum(1 for row in all_rows if row.movement_type == "IN"),
                "outbound": sum(1 for row in all_rows if row.movement_type == "OUT"),
                "in_qty": sum(row.qty or 0 for row in all_rows if row.movement_type == "IN"),
                "out_qty": sum(row.qty or 0 for row in all_rows if row.movement_type == "OUT"),
                "set_jobs": len({row.request_id for row in all_rows if row.request_id}),
                "lots": len({row.lot for row in all_rows if row.lot}),
            },
            "page": page,
            "total_pages": total_pages,
            "movement_type": movement_type,
            "keyword": keyword,
            "category": category,
            "format_kst": format_kst,
        }
    )

@router.get("/stock/download-excel")
def download_stock_excel(
    request: Request,
    db: Session = Depends(get_db)
):

    items = (
        db.query(Stock)
        .order_by(Stock.item_code)
        .all()
    )

    raw_ids = [item.id for item in items if item.category == "원자재"]
    lot_rows = db.query(StockLot).filter(StockLot.stock_id.in_(raw_ids)).order_by(StockLot.stock_id, StockLot.first_received_date, StockLot.lot).all() if raw_ids else []
    lots_by_stock = {}
    for lot_row in lot_rows:
        lots_by_stock.setdefault(lot_row.stock_id, []).append(lot_row)

    rows = []
    for item in items:
        base = {"품목코드": item.item_code, "품명": item.item_name, "등급": item.grade, "Rev": item.rev, "구분": item.category}
        item_lots = lots_by_stock.get(item.id, []) if item.category == "원자재" else []
        if not item_lots:
            rows.append({**base, "LOT": "", "최초 입고일자": "", "검사원": "", "수량": item.qty})
            continue
        tracked = 0
        for lot_row in item_lots:
            tracked += lot_row.qty or 0
            rows.append({
                **base,
                "LOT": lot_row.lot,
                "최초 입고일자": lot_row.first_received_date.isoformat() if lot_row.first_received_date else "",
                "검사원": lot_row.inspector or "",
                "수량": lot_row.qty or 0,
            })
        unclassified = max((item.qty or 0) - tracked, 0)
        if unclassified:
            rows.append({**base, "LOT": "", "최초 입고일자": "", "검사원": "", "수량": unclassified})

    df = pd.DataFrame(rows)

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Stock"
        )

    output.seek(0)

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_DOWNLOAD_EXCEL",
        detail=f"가계상 재고 엑셀 다운로드: {len(items)}건"
    )

    return StreamingResponse(
        output,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": download_content_disposition(
                "가계상 재고 현황", "stock"
            )
        }
    )


@router.get("/stock/lot-upload-template")
def download_stock_lot_upload_template():
    sample = pd.DataFrame([{"품목코드": "RAW-001", "Grade": "A", "LOT": "LOT-20261103-01", "수량": 100, "최초 입고일자": "2026-11-03", "검사원": "quality01"}])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="가계상 원자재 LOT 등록")
        sheet = writer.sheets["가계상 원자재 LOT 등록"]
        for column, width in {"A": 20, "B": 12, "C": 24, "D": 12, "E": 18, "F": 16}.items():
            sheet.column_dimensions[column].width = width
        sheet.freeze_panes = "A2"
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": download_content_disposition("가계상 원자재 LOT 업로드 예시", "stock-raw-lot-upload-template")})


@router.post("/stock/lot-upload")
async def upload_stock_lot_excel(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = pd.read_excel(file.file)
    except Exception as exc:
        return JSONResponse({"status": "error", "message": f"엑셀 파일을 읽을 수 없습니다. ({type(exc).__name__})"}, status_code=400)
    required = ["품목코드", "Grade", "LOT", "수량"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        return JSONResponse({"status": "error", "message": f"필수 컬럼이 없습니다: {', '.join(missing)}"}, status_code=400)
    date_column = next((column for column in ("최초 입고일자", "입고일자") if column in df.columns), None)
    inspector_column = "검사원" if "검사원" in df.columns else None
    prepared = []
    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        item_code = "" if pd.isna(row["품목코드"]) else normalize_item_code(row["품목코드"])
        grade = str(row["Grade"]).strip().upper() if pd.notna(row["Grade"]) else ""
        lot = str(row["LOT"]).strip() if pd.notna(row["LOT"]) else ""
        try:
            qty = int(row["수량"])
        except (TypeError, ValueError):
            return JSONResponse({"status": "error", "message": f"엑셀 {row_number}행의 수량을 확인하세요."}, status_code=400)
        if not item_code or grade not in {"A", "B", "F"} or not lot or qty < 0:
            return JSONResponse({"status": "error", "message": f"엑셀 {row_number}행의 품목코드, Grade, LOT, 수량을 확인하세요."}, status_code=400)
        try:
            raw_date = None if date_column is None else row[date_column]
            received_date = None if raw_date is None or pd.isna(raw_date) else pd.to_datetime(raw_date).date()
        except Exception:
            return JSONResponse({"status": "error", "message": f"엑셀 {row_number}행의 입고일자를 확인하세요."}, status_code=400)
        inspector_name = "" if inspector_column is None or pd.isna(row[inspector_column]) else str(row[inspector_column]).strip()
        item = db.query(Stock).filter(Stock.item_code == item_code, Stock.category == "원자재", Stock.grade == grade).first()
        if item is None:
            return JSONResponse({"status": "error", "message": f"엑셀 {row_number}행에 해당하는 원자재가 없습니다: {item_code} / {grade}"}, status_code=400)
        prepared.append((item, lot[:100], qty, received_date, inspector_name[:100]))
    username = current_user(request)
    for item, lot, qty, received_date, inspector_name in prepared:
        lot_row = stock_lot_row(db, item, lot)
        if lot_row is None:
            lot_row = StockLot(stock_id=item.id, item_code=item.item_code, grade=item.grade, lot=lot, qty=0)
            db.add(lot_row)
        lot_row.qty = (lot_row.qty or 0) + qty
        if received_date and not lot_row.first_received_date:
            lot_row.first_received_date = received_date
        if inspector_name:
            lot_row.inspector = inspector_name
        if qty > 0:
            item.qty = (item.qty or 0) + qty
            db.add(StockMovement(item_code=item.item_code, item_name=item.item_name, category=item.category, movement_type="IN", qty=qty, user=username, source="LOT 엑셀 업로드", grade=item.grade, lot=lot, inspector=inspector_name, first_received_date=received_date))
    db.commit()
    total_qty = sum(qty for _, _, qty, _, _ in prepared)
    message = f"LOT {len(prepared)}건 등록 / 입고 {total_qty} EA"
    save_log(user=username, product=STOCK_LOG_PRODUCT, action="STOCK_LOT_UPLOAD_EXCEL", detail=f"가계상 원자재 LOT 엑셀 업로드: {message}")
    return {"status": "success", "created": len(prepared), "qty": total_qty, "message": message}

@router.get("/stock/item-master")
def get_item_master(
    code: str,
    db: Session = Depends(get_db)
):

    item = (
        db.query(ItemMaster)
        .filter(
            ItemMaster.item_code == code
        )
        .first()
    )

    if not item:

        return {
            "exists": False
        }

    return {
        "exists": True,
        "item_name": item.item_name,
        "rev": item.rev
    }

@router.post("/stock/init-excel")
async def init_stock_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    created = 0
    skipped = 0

    for _, row in df.iterrows():

        item_code = normalize_item_code(
            row["품목코드"]
        )

        category = str(
            row["구분"]
        ).strip()

        master = (
            db.query(ItemMaster)
            .filter(
                ItemMaster.item_code == item_code
            )
            .first()
        )

        if not master:

            skipped += 1
            continue

        for grade in ["A", "B", "F"]:

            exists = (
                db.query(Stock)
                .filter(
                    Stock.item_code == item_code,
                    Stock.grade == grade
                )
                .first()
            )

            if exists:
                continue

            db.add(
                Stock(
                    item_code=item_code,
                    item_name=master.item_name,
                    grade=grade,
                    rev=master.rev,
                    category=category,
                    qty=0
                )
            )

            created += 1

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_INIT_EXCEL",
        detail=(
            f"초기 품목 생성 "
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

@router.post("/stock/upload-excel")
async def upload_stock_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    created = 0
    updated = 0
    skipped = 0

    for _, row in df.iterrows():

        item_code = normalize_item_code(
            row["품목코드"]
        )

        category = str(
            row["구분"]
        ).strip()

        grade = str(
            row["등급"]
        ).strip()

        qty = int(
            row["수량"]
        ) if pd.notna(row["수량"]) else 0

        master = (
            db.query(ItemMaster)
            .filter(
                ItemMaster.item_code == item_code
            )
            .first()
        )

        if not master:

            skipped += 1
            continue

        stock = (
            db.query(Stock)
            .filter(
                Stock.item_code == item_code,
                Stock.grade == grade
            )
            .first()
        )

        if stock:

            stock.item_name = master.item_name
            stock.rev = master.rev
            stock.category = category
            stock.qty = qty

            updated += 1

        else:

            db.add(
                Stock(
                    item_code=item_code,
                    item_name=master.item_name,
                    grade=grade,
                    rev=master.rev,
                    category=category,
                    qty=qty
                )
            )

            created += 1

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_UPLOAD_EXCEL",
        detail=(
            f"가계상 재고 업로드 "
            f"(신규 {created}건 / 수정 {updated}건 / 제외 {skipped}건)"
        )
    )

    return JSONResponse(
        {
            "status": "success",
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "message":
                f"신규 {created}건 / 수정 {updated}건 / 제외 {skipped}건"
        }
    )

@router.post("/stock/update-qty")
async def update_qty(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    item = (
        db.query(Stock)
        .filter(
            Stock.id == data["id"]
        )
        .first()
    )

    if not item:
        return {
            "status":"error"
        }

    old_qty = item.qty

    new_qty = int(
        data["qty"]
    )

    item.qty = new_qty

    db.add(
        StockMovement(
            item_code=item.item_code,
            item_name=item.item_name,
            category=item.category,
            movement_type="ADJUST",
            qty=new_qty - old_qty,
            user="admin",
            source="manual_edit"
        )
    )

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_UPDATE_QTY",
        serial=item.item_code,
        detail=f"{item.item_name} 수량 변경: {old_qty} -> {new_qty}"
    )

    return {
        "status":"success"
    }

@router.post("/stock/update-grade")
async def update_grade(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    item = (
        db.query(Stock)
        .filter(
            Stock.id == data["id"]
        )
        .first()
    )

    if not item:
        return {"status": "error"}

    old_grade = item.grade
    item.grade = data["grade"]

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_UPDATE_GRADE",
        serial=item.item_code,
        detail=f"{item.item_name} Grade 변경: {old_grade or '-'} -> {item.grade or '-'}"
    )

    return {"status": "success"}

@router.post("/stock/bulk-update-grade")
async def bulk_update_grade(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data["ids"]
    grade = data["grade"]

    items = (
        db.query(Stock)
        .filter(
            Stock.id.in_(ids)
        )
        .all()
    )

    for item in items:

        item.grade = grade

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_BULK_UPDATE_GRADE",
        serial=summarize_items(items),
        detail=f"가계상 재고 Grade 일괄 변경: {len(items)}건 -> {grade}"
    )

    return {
        "status":"success"
    }

@router.post("/stock/bulk-update-qty")
async def bulk_update_qty(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    ids = data["ids"]
    qty = int(data["qty"])

    items = (
        db.query(Stock)
        .filter(
            Stock.id.in_(ids)
        )
        .all()
    )

    for item in items:

        item.qty = qty

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_BULK_UPDATE_QTY",
        serial=summarize_items(items),
        detail=f"가계상 재고 수량 일괄 변경: {len(items)}건 -> {qty} EA"
    )

    return {
        "status":"success"
    }

@router.get("/stock/history/download-excel")
def download_history_excel(
    request: Request,
    db: Session = Depends(get_db)
):

    history = (
        db.query(StockMovement)
        .order_by(
            StockMovement.created_at.desc()
        )
        .all()
    )

    data = []

    for row in history:

        data.append({

            "일시": format_kst(row.created_at),

            "품목코드":
                row.item_code,

            "품명":
                row.item_name,

            "구분":
                row.category,

            "유형":
                "입고"
                if row.movement_type == "IN"
                else "출고",

            "수량":
                row.qty,

            "등급": row.grade or "",

            "LOT": row.lot or "",

            "검사원": row.inspector or "",

            "최초 입고일자": row.first_received_date.isoformat() if row.first_received_date else "",

            "세트 구성품": row.set_component or "",

            "세트 수량": row.set_count or "",

            "처리번호": row.request_id or "",

            "작업자":
                row.user,

            "비고":
                row.source
        })

    df = pd.DataFrame(data)

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".xlsx"
    )

    df.to_excel(
        temp_file.name,
        index=False
    )

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_HISTORY_DOWNLOAD_EXCEL",
        detail=f"가계상 재고 입출고 이력 다운로드: {len(history)}건"
    )

    return FileResponse(
        temp_file.name,
        filename=dated_filename("가계상 재고 입출고 이력"),
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/stock/item-master/manage")
def item_master_page(
    request: Request,
    db: Session = Depends(get_db)
):

    items = (
        db.query(ItemMaster)
        .order_by(ItemMaster.item_code)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="stock/item_master.html",
        context={
            "items": items
        }
    )

@router.post("/stock/item-master/update")
def update_item(
    request: Request,
    data: dict,
    db: Session = Depends(get_db)
):
    
    user = (
        request.session.get("user")
        or "system"
    )
    try:

        item = (
            db.query(ItemMaster)
            .filter(
                ItemMaster.id == data["id"]
            )
            .first()
        )

        if not item:
            return {
                "status":"error",
                "message":"품목을 찾을 수 없습니다."
            }

        old_code = item.item_code
        old_name = item.item_name
        old_rev = item.rev

        new_code = normalize_item_code(
            data["item_code"]
        )
        new_name = data["item_name"].strip()
        new_rev = (data.get("rev") or "").strip()

        if (
            old_code == new_code
            and old_name == new_name
            and old_rev == new_rev
        ):
            return {
                "status": "error",
                "message": "변경된 내용이 없습니다."
            }

        duplicate = (
            db.query(ItemMaster)
            .filter(
                ItemMaster.item_code == new_code,
                ItemMaster.id != item.id
            )
            .first()
        )

        if duplicate:
            return {
                "status":"error",
                "message":"이미 존재하는 품목코드입니다."
            }

        item.item_code = new_code
        item.item_name = new_name
        item.rev = new_rev

        stocks = (
            db.query(Stock)
            .filter(
                Stock.item_code == old_code
            )
            .all()
        )

        for stock in stocks:
            stock.item_code = new_code
            stock.item_name = new_name
            stock.rev = new_rev

        movements = (
            db.query(StockMovement)
            .filter(
                StockMovement.item_code == old_code
            )
            .all()
        )

        for movement in movements:
            movement.item_code = new_code
            movement.item_name = new_name
        
        boms = (
            db.query(BOM)
            .filter(
                BOM.component_code == old_code
            )
            .all()
        )

        for bom in boms:

            bom.component_code = new_code
            bom.component_name = new_name

        inventories = (
            db.query(Inventory)
            .filter(
                Inventory.item_code == old_code
            )
            .all()
        )

        for inv in inventories:

            inv.item_code = new_code
            inv.item_name = new_name

        materials = (
            db.query(MaterialMaster)
            .filter(
                MaterialMaster.item_code == old_code
            )
            .all()
        )

        for material in materials:

            material.item_code = new_code
            material.item_name = new_name

        notes = (
            db.query(MaterialNote)
            .filter(
                MaterialNote.item_code == old_code
            )
            .all()
        )

        for note in notes:

            note.item_code = new_code

        db.add(
            ItemMasterHistory(
                old_code=old_code,
                new_code=new_code,

                old_name=old_name,
                new_name=new_name,

                old_rev=old_rev,
                new_rev=new_rev,

                user=user
            )
        )

        db.commit()

        save_log(
            user=user,
            product=STOCK_LOG_PRODUCT,
            action="STOCK_ITEM_MASTER_UPDATE",
            serial=f"{old_code} -> {new_code}",
            detail=f"품목 기준정보 변경: {old_name} / Rev {old_rev or '-'} -> {new_name} / Rev {new_rev or '-'}"
        )

        return {
            "status":"success"
        }

    except Exception as e:

        db.rollback()

        return {
            "status":"error",
            "message": str(e)
        }
    
@router.get("/stock/item-master/history")
def item_master_history(
    request: Request,
    db: Session = Depends(get_db)
):

    history = (
        db.query(ItemMasterHistory)
        .order_by(
            ItemMasterHistory.created_at.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="stock/item_master_history.html",
        context={
            "history": history
        }
    )

@router.post("/stock/item-master/upload")
async def upload_item_master(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    created = 0
    skipped = 0

    for _, row in df.iterrows():

        item_code = normalize_item_code(
            row["품목코드"]
        )

        item_name = str(
            row["품명"]
        ).strip()

        rev = str(
            row["Rev"]
        ).strip()

        exists = (
            db.query(ItemMaster)
            .filter(
                ItemMaster.item_code == item_code
            )
            .first()
        )

        if exists:

            skipped += 1
            continue

        db.add(
            ItemMaster(
                item_code=item_code,
                item_name=item_name,
                rev=rev
            )
        )

        created += 1

    db.commit()

    save_log(
        user=current_user(request),
        product=STOCK_LOG_PRODUCT,
        action="STOCK_ITEM_MASTER_UPLOAD",
        detail=f"품목 기준정보 업로드: 신규 {created}건 / 제외 {skipped}건"
    )

    return {
        "status": "success",
        "created": created,
        "skipped": skipped,
        "message":
            f"신규 {created}건 / 제외 {skipped}건"
    }
