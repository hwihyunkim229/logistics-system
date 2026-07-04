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
import pandas as pd
from io import BytesIO
from app.models.item_master import ItemMaster
from app.models.item_master_history import ItemMasterHistory
from fastapi import UploadFile, File
import tempfile
from math import ceil
from sqlalchemy import or_
from app.models.bom import BOM
from app.models.inventory import Inventory
from app.models.material_master import MaterialMaster
from app.models.material_note import MaterialNote
from app.utils.logger import save_log

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


@router.get("/stock")
def inventory_dashboard(
    request: Request,
    category: str = "반제품",
    page: int = 1,
    keyword: str = "",
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

    total_pages = max(
        1,
        ceil(total_count / per_page)
    )

    all_items = db.query(Stock).all()

    semi_qty = sum(
        x.qty for x in all_items
        if x.category == "반제품"
    )

    product_qty = sum(
        x.qty for x in all_items
        if x.category == "제품"
    )

    raw_qty = sum(
        x.qty for x in all_items
        if x.category == "원자재"
    )

    return templates.TemplateResponse(
        request=request,
        name="stock/index.html",
        context={
            "items": items,
            "current_category": category,
            "page": page,
            "keyword": keyword,
            "total_pages": total_pages,
            "semi_qty": semi_qty,
            "product_qty": product_qty,
            "raw_qty": raw_qty
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
                source=remark
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
                source=remark
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
    movement_type: str = "IN",
    page: int = 1,
    keyword: str = "",
    category: str = "",
    db: Session = Depends(get_db)
):

    per_page = 50

    query = (
        db.query(StockMovement)
        .filter(
            StockMovement.movement_type
            == movement_type
        )
    )

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

    if category:

        query = query.filter(
            StockMovement.category == category
        )

    query = query.order_by(
        StockMovement.created_at.desc()
    )

    total_count = query.count()

    history = (
        query
        .offset(
            (page - 1) * per_page
        )
        .limit(per_page)
        .all()
    )

    total_pages = max(
        1,
        ceil(total_count / per_page)
    )

    return templates.TemplateResponse(
        request=request,
        name="stock/history.html",
        context={
            "history": history,
            "page": page,
            "total_pages": total_pages,
            "movement_type": movement_type,
            "keyword": keyword,
            "category": category
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

    rows = []

    for item in items:

        rows.append(
            {
                "품목코드": item.item_code,
                "품명": item.item_name,
                "등급": item.grade,
                "Rev": item.rev,
                "구분": item.category,
                "수량": item.qty
            }
        )

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
            "Content-Disposition":
            "attachment; filename=stock.xlsx"
        }
    )

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

@router.post("/stock/upload-excel")
async def upload_stock_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    df = pd.read_excel(file.file)

    created = 0
    skipped = 0

    for _, row in df.iterrows():

        item_code = str(
            row["품목코드"]
        ).strip()

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
        action="STOCK_UPLOAD_EXCEL",
        detail=f"가계상 재고 엑셀 업로드: 신규 {created}건 / 제외 {skipped}건"
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

            "일시":
                row.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

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
        filename="stock_history.xlsx",
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

        new_code = data["item_code"].strip()
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

        item_code = str(
            row["품목코드"]
        ).strip()

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
