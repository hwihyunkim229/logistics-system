from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import SessionLocal
from app.models.outbound import Outbound
from app.models.inbound import Inbound
from fastapi.responses import RedirectResponse
import pandas as pd
from datetime import date
from app.models.movement import Movement
from sqlalchemy import or_
from sqlalchemy import cast, String
from datetime import datetime
from sqlalchemy import func, case
from fastapi.responses import StreamingResponse
import io
from app.utils.logger import save_log
from zoneinfo import ZoneInfo

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

SERVICES = [
    "cart_bp_pro",
    "cart_bp",
    "cart_on",
    "hanbang",
    "cart_platform",
    "cart_ring",
    "cart_o2"
]

SERVICE_NAMES = {
    "cart_bp_pro": "CART BP pro",
    "cart_bp": "CART BP",
    "cart_on": "CART ON",
    "hanbang": "한방 병원",
    "cart_platform" : "CART PLATFORM",
    "cart_ring" : "CART RING",
    "cart_o2" : "CART O2"
}

def parse_date(value):
    from datetime import datetime, date

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        value = value.strip()

        for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"]:
            try:
                return datetime.strptime(value.replace(" ", ""), fmt).date()
            except:
                continue

    return None

@router.get("/search", response_class=HTMLResponse)
def global_search(
    request: Request,
    q: str = "",
    status: str = "",
    start_date: str = "",
    end_date: str = ""
    ):

    db = SessionLocal()

    outbound = db.query(Outbound)
    inbound = db.query(Inbound)

    # =========================
    # 상태 필터
    # =========================

    if status == "outbound":
        inbound = inbound.filter(False)

    elif status == "inbound":
        outbound = outbound.filter(False)

    # =========================
    # 검색어 필터
    # =========================
    search_product = q

    for product_key, product_name in SERVICE_NAMES.items():

        if q.lower() in product_name.lower():

            search_product = product_key

            break

    if q:

        outbound = outbound.filter(
            or_(
                Outbound.serial.contains(q),
                Outbound.client.contains(q),
                Outbound.note.contains(q),
                Outbound.category.contains(q),
                Outbound.product.contains(search_product),
                cast(Outbound.size, String).contains(q)
            )
        )

        inbound = inbound.filter(
            or_(
                Inbound.serial.contains(q),
                Inbound.client.contains(q),
                Inbound.note.contains(q),
                Inbound.category.contains(q),
                Inbound.product.contains(search_product),
                cast(Inbound.size, String).contains(q)
            )
        )

    # =========================
    # 날짜 필터
    # =========================

    if start_date:

        start = datetime.combine(
            datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date(),
            datetime.min.time()
        )

        outbound = outbound.filter(
            Outbound.created_at >= start
        )

        inbound = inbound.filter(
            Inbound.created_at >= start
        )

    if end_date:

        end = datetime.combine(
            datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date(),
            datetime.max.time()
        )

        outbound = outbound.filter(
            Outbound.created_at <= end
        )

        inbound = inbound.filter(
            Inbound.created_at <= end
        )

    # =========================
    # 데이터 조회
    # =========================

    outbound_data = outbound.order_by(
        Outbound.id.asc()
    ).all()

    inbound_data = inbound.order_by(
        Inbound.id.asc()
    ).all()

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="search_all.html",
        context={

            "outbound": outbound_data,
            "inbound": inbound_data,

            "q": q,
            "status": status,

            "start_date": start_date,
            "end_date": end_date,

            "mode": "search_all",

            # 🔥 Product 한글화용
            "SERVICE_NAMES": SERVICE_NAMES
        }
    )

@router.get("/history-api/{serial}")
def get_history_api(serial: str):

    db = SessionLocal()

    logs = db.query(Movement)\
        .filter(Movement.serial == serial)\
        .order_by(Movement.created_at.asc())\
        .all()

    db.close()

    return [
        {
            "type": log.type,
            "source": log.source,
            "product": log.product,
            "client": log.client,
            "user": log.user,
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for log in logs
    ]

@router.get("/product/{product}/{mode}", response_class=HTMLResponse)
def main_page(
    request: Request,
    product: str,
    mode: str,
    sort: str = "date",
    order: str = "desc",
    page: int = 1
):
    db = SessionLocal()

    per_page = 50

    # =========================
    # OUTBOUND
    # =========================

    if mode == "outbound":

        query = db.query(Outbound)\
            .filter(Outbound.product == product)
        
        if sort == "date":
            query = query.order_by(
                Outbound.created_at.desc()
                if order == "desc"
                else Outbound.created_at.asc()
            )

        elif sort == "size":
            query = query.order_by(
                Outbound.size.desc()
                if order == "desc"
                else Outbound.size.asc()
            )

        total_count = query.count()

        total_pages = (
            total_count + per_page - 1
        ) // per_page

        data = query\
            .order_by(Outbound.id.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

    # =========================
    # INBOUND
    # =========================

    elif mode == "inbound":

        query = db.query(Inbound)\
            .filter(Inbound.product == product)

        if sort == "date":
            query = query.order_by(
                Inbound.created_at.desc()
                if order == "desc"
                else Inbound.created_at.asc()
            )

        elif sort == "size":
            query = query.order_by(
                Inbound.size.desc()
                if order == "desc"
                else Inbound.size.asc()
            )

        total_count = query.count()

        total_pages = (
            total_count + per_page - 1
        ) // per_page

        data = query\
            .order_by(Inbound.id.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

    else:

        data = []
        total_pages = 1

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "data": data,
            "product": product,
            "mode": mode,
            "page": page,
            "sort": sort,
            "order": order,
            "total_pages": total_pages
        }
    )

@router.post("/upload/{product}/{mode}")
async def upload_excel(request: Request, product: str, mode: str, file: UploadFile = File(...)):
    username = request.session.get("user", "unknown")
    df = pd.read_excel(file.file)

    df.columns = [c.strip() for c in df.columns]

    date_col = [
        c for c in df.columns
        if "출고" in c or "입고" in c
    ][0]

    serial_col = [c for c in df.columns if "serial" in c.lower()][0]
    size_col = [c for c in df.columns if "size" in c.lower() or "호수" in c][0]

    db = SessionLocal()

    created_count = 0
    duplicate_count = 0

    category_col = next((c for c in df.columns if "구분" in c), None)

    client_col = next(
        (c for c in df.columns if "출고처" in c),
        None
    )

    for _, row in df.iterrows():
        date_val = row[date_col]
        serial = str(row[serial_col]).strip().upper()
        size = str(row[size_col]).strip()
        category = str(row[category_col]).strip() if category_col else None
        client = (
            str(row[client_col]).strip()
            if client_col else None
        )

        if not serial or serial == "nan":
            continue

        date_val = parse_date(date_val)

        if size and size != "nan":
            size = str(int(float(size)))
        else:
            size = None

        if mode == "outbound":
            db.add(Outbound(
                serial=serial,
                size=size,
                category=category,
                client=client,
                created_at=datetime.combine(
                    date_val,
                    datetime.now(
                        ZoneInfo("Asia/Seoul")
                    ).time()
                ),
                product=product
            ))

            db.add(Movement(
                serial=serial,
                product=product,
                type="OUT",
                source="excel",
                category=category,
                client=client,
                user=username,
                created_at = datetime.combine(
                                date_val,
                                datetime.now(
                                    ZoneInfo("Asia/Seoul")
                                ).time()
                            )
            ))

        elif mode == "inbound":
            db.add(Inbound(
                serial=serial,
                size=size,
                category=category,
                client=client,
                created_at=datetime.combine(
                    date_val,
                    datetime.now(
                        ZoneInfo("Asia/Seoul")
                    ).time()
                ),
                product=product
            ))

            db.add(Movement(
                serial=serial,
                product=product,
                type="IN",
                source="excel",
                category=category,
                client=client,
                user=username,
                created_at = datetime.combine(
                                date_val,
                                datetime.now(
                                    ZoneInfo("Asia/Seoul")
                                ).time()
                            )
            ))

        created_count += 1

    db.commit()

    service_name = SERVICE_NAMES.get(
        product,
        product
    )

    save_log(
        user=username,
        product=service_name,
        action="UPLOAD_EXCEL",
        serial="",
        detail=(
            f"{mode} | "
            f"생성:{created_count} | "
        )
    )

    db.close()

    return {
        "total": len(df),
        "created": created_count
    }

@router.post("/update-size")
async def update_size(
    request: Request,
    data: dict
):
    db = SessionLocal()

    ids = data.get("ids")
    size = data.get("size")
    mode = data.get("mode")

    if mode == "outbound":
        db.query(Outbound)\
            .filter(Outbound.id.in_(ids))\
            .update({"size": size}, synchronize_session=False)

    elif mode == "inbound":
        db.query(Inbound)\
            .filter(Inbound.id.in_(ids))\
            .update({"size": size}, synchronize_session=False)

    user = request.session.get(
        "user",
        "unknown"
    )

    Model = Outbound if mode == "outbound" else Inbound

    items = db.query(Model).filter(
        Model.id.in_(ids)
    ).all()

    serials = [
        item.serial for item in items
    ]

    preview = ", ".join(
        serials[:5]
    )

    service_name = SERVICE_NAMES.get(
        items[0].product,
        items[0].product
    ) if items else mode


    db.commit()

    save_log(
        user=user,
        product=service_name,
        action="UPDATE_SIZE",
        serial=preview,
        detail=(
            f"size={size} | "
            f"{len(ids)}건 수정"
        )
    )

    db.close()

    return {"status": "ok"}

@router.post("/delete-selected")
async def delete_selected(
    data: dict,
    request: Request
):
    db = SessionLocal()

    ids = data.get("ids")
    mode = data.get("mode")

    user = request.session.get("user")

    # =========================
    # OUTBOUND 삭제
    # =========================

    if mode == "outbound":

        items = db.query(Outbound).filter(
            Outbound.id.in_(ids)
        ).all()

        for item in items:

            log = Movement(
                product=item.product,
                serial=item.serial,
                type="DELETE_OUT",
                client=item.client,
                user=user,
                created_at=datetime.now(
                    ZoneInfo("Asia/Seoul")
                )
            )

            db.add(log)

            db.delete(item)

    # =========================
    # INBOUND 삭제
    # =========================

    elif mode == "inbound":

        items = db.query(Inbound).filter(
            Inbound.id.in_(ids)
        ).all()

        for item in items:

            log = Movement(
                product=item.product,
                serial=item.serial,
                type="DELETE_IN",
                client=None,
                user=user,
                created_at=datetime.now(
                    ZoneInfo("Asia/Seoul")
                )
            )

            db.add(log)

            db.delete(item)

    # =========================
    # activity 로그
    # =========================

    preview = ", ".join(
        [item.serial for item in items[:5]]
    )

    service_name = SERVICE_NAMES.get(
        items[0].product,
        items[0].product
    ) if items else mode

    db.commit()

    save_log(
        user=user,
        product=service_name,
        action="DELETE_SELECTED",
        serial=preview,
        detail=f"{len(ids)}건 삭제"
    )

    db.close()

    return {"status": "ok"}

@router.post("/delete-all")
async def delete_all(
    data: dict,
    request: Request
):
    db = SessionLocal()

    mode = data.get("mode")

    user = request.session.get("user")

    if mode == "outbound":

        items = db.query(Outbound).all()

        for item in items:

            log = Movement(
                product=item.product,
                serial=item.serial,
                type="DELETE_OUT",
                client=item.client,
                user=user,
                created_at=datetime.now(
                    ZoneInfo("Asia/Seoul")
                )
            )

            db.add(log)

            db.delete(item)

    elif mode == "inbound":

        items = db.query(Inbound).all()

        for item in items:

            log = Movement(
                product=item.product,
                serial=item.serial,
                type="DELETE_IN",
                client=None,
                user=user,
                created_at=datetime.now(
                    ZoneInfo("Asia/Seoul")
                )
            )

            db.add(log)

            db.delete(item)

    preview = ", ".join(
        [item.serial for item in items[:5]]
    )

    service_name = SERVICE_NAMES.get(
        items[0].product,
        items[0].product
    ) if items else mode

    db.commit()

    save_log(
        user=user,
        product=service_name,
        action="DELETE_ALL",
        serial=preview,
        detail=f"{len(items)}건 전체 삭제"
    )

    db.close()

    return {"status": "ok"}

@router.post("/move-to-inbound")
async def move_to_inbound(request: Request, data: dict):
    username = request.session.get("user", "unknown")
    db = SessionLocal()

    ids = data.get("ids")

    items = db.query(Outbound)\
        .filter(Outbound.id.in_(ids))\
        .all()

    moved_count = 0

    serials = []
    service_name = ""

    for item in items:
        db.refresh(item)

        exists = db.query(Inbound).filter(
            Inbound.serial == item.serial,
            Inbound.product == item.product
        ).first()

        if exists:
            continue

        db.add(Inbound(
            serial=item.serial,
            size=item.size,
            product=item.product,
            created_at=datetime.now(
                ZoneInfo("Asia/Seoul")
            ),
            category=item.category,
            client=item.client,
            note=item.note
        ))

        db.add(Movement(
            serial=item.serial,
            product=item.product,
            type="MOVE_IN",
            source="move",
            user=username,
            created_at=datetime.now(
                ZoneInfo("Asia/Seoul")
            )
        ))

        db.delete(item)

        moved_count += 1

        serials.append(item.serial)

        service_name = SERVICE_NAMES.get(
            item.product,
            item.product
        )

    preview = ", ".join(
        serials[:5]
    )

    db.commit()

    save_log(
        user=username,
        product=service_name,
        action="MOVE_IN",
        serial=preview,
        detail=f"{moved_count}건 입고 이동"
    )

    db.close()

    return {
        "status": "ok",
        "moved": moved_count
    }

@router.post("/move-to-outbound")
async def move_to_inbound(request: Request, data: dict):
    username = request.session.get("user", "unknown")
    db = SessionLocal()

    ids = data.get("ids")

    items = db.query(Inbound)\
        .filter(Inbound.id.in_(ids))\
        .all()

    moved_count = 0

    serials = []
    service_name = ""

    for item in items:
        # 🔥 중복 방지 (출고 기준)
        exists = db.query(Outbound).filter(
            Outbound.serial == item.serial,
            Outbound.product == item.product
        ).first()

        if exists:
            continue

        # 🔥 outbound 추가
        db.add(Outbound(
            serial=item.serial,
            size=item.size,
            product=item.product,
            created_at=datetime.now(
                ZoneInfo("Asia/Seoul")
            ),
            category=item.category,
            client=item.client,
            note=item.note
        ))

        db.add(Movement(
            serial=item.serial,
            product=item.product,
            type="MOVE_OUT",
            source="move",
            user=username,
            created_at=datetime.now(
                ZoneInfo("Asia/Seoul")
            )
        ))

        # 🔥 inbound 삭제
        db.delete(item)

        moved_count += 1

        service_name = SERVICE_NAMES.get(
            item.product,
            item.product
        )

    preview = ", ".join(
        serials[:5]
    )

    db.commit()

    save_log(
        user=username,
        product=service_name,
        action="MOVE_OUT",
        serial=preview,
        detail=f"{moved_count}건 출고 이동"
    )

    db.close()

    return {
        "status": "ok",
        "moved": moved_count
    }

@router.post("/update-field")
async def update_field(
    request: Request,
    data: dict
):
    db = SessionLocal()

    id = data.get("id")
    field = data.get("field")
    value = data.get("value")
    mode = data.get("mode")

    if mode == "outbound":
        item = db.query(Outbound).filter(Outbound.id == id).first()
    else:
        item = db.query(Inbound).filter(Inbound.id == id).first()

    if item and hasattr(item, field):
        setattr(item, field, value)

    user = request.session.get(
        "user",
        "unknown"
    )

    service_name = SERVICE_NAMES.get(
        item.product,
        item.product
    )

    db.commit()

    save_log(
        user=user,
        product=service_name,
        action="UPDATE_FIELD",
        serial=item.serial,
        detail=f"{field}={value}"
    )

    db.close()

    return {"status": "ok"}

@router.get("/inventory")
def get_inventory():
    db = SessionLocal()

    # 🔥 stock 계산
    result = db.query(
        Movement.serial,
        Movement.product,
        func.sum(
            case(
                (Movement.type == "IN", 1),
                (Movement.type == "OUT", -1),
                else_=0
            )
        ).label("stock")
    ).group_by(
        Movement.serial,
        Movement.product
    ).all()

    inventory = []

    for r in result:
        # 🔥 마지막 movement 조회 (핵심)
        latest = db.query(Movement)\
            .filter(Movement.serial == r.serial)\
            .order_by(Movement.created_at.desc())\
            .first()

        if latest:
            if latest.type == "IN":
                status = "IN"
            elif latest.type == "OUT":
                status = "OUT"
            else:
                status = "UNKNOWN"
        else:
            status = "UNKNOWN"

        inventory.append({
            "serial": r.serial,
            "product": r.product,
            "stock": r.stock,
            "status": status
        })

    db.close()
    return inventory

@router.get("/inventory-page", response_class=HTMLResponse)
def inventory_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context={}
    )

@router.get(
    "/movement-history/{serial}",
    response_class=HTMLResponse
)
def movement_history(
    request: Request,
    serial: str
):

    db = SessionLocal()

    records = db.query(Movement)\
        .filter(Movement.serial == serial)\
        .order_by(Movement.created_at.asc())\
        .all()

    # =========================
    # 현재 상태
    # =========================

    latest = records[-1] if records else None

    current_status = (
        latest.type if latest else "UNKNOWN"
    )

    # =========================
    # 서비스명
    # =========================

    service_name = ""

    if records:

        service_name = SERVICE_NAMES.get(
            records[0].product,
            records[0].product
        )

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "serial": serial,
            "records": records,
            "current_status": current_status,
            "SERVICE_NAMES": SERVICE_NAMES,
            "service_name": service_name
        }
    )

@router.post("/bulk-update")
async def bulk_update(
    request: Request,
    data: dict
):

    db = SessionLocal()

    try:

        ids = data.get("ids", [])
        field = data.get("field")
        value = data.get("value")
        mode = data.get("mode")

        # 🔥 테이블 선택
        Model = Outbound if mode == "outbound" else Inbound

        # 🔥 한번에 조회
        items = (
            db.query(Model)
            .filter(Model.id.in_(ids))
            .all()
        )

        serials = []

        for item in items:

            serials.append(item.serial)

            if field == "size":
                item.size = str(value)

            elif field == "category":
                item.category = value

            elif field == "client":
                item.client = value

            elif field == "note":
                item.note = value

        # 🔥 먼저 commit
        db.commit()

        user = request.session.get(
            "user",
            "unknown"
        )

        preview = ", ".join(
            serials[:5]
        )

        service_name = (
            SERVICE_NAMES.get(
                items[0].product,
                items[0].product
            )
            if items else mode
        )

        # 🔥 commit 끝난 뒤 로그 저장
        try:
            save_log(
                user=user,
                product=service_name,
                action="BULK_UPDATE",
                serial=preview,
                detail=(
                    f"{field}={value} | "
                    f"{len(serials)}건 수정"
                )
            )
        except Exception as log_error:
            print("로그 저장 실패:", log_error)

        return {"status": "ok"}

    except Exception as e:
        db.rollback()
        print(e)

        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        db.close()

@router.get("/download-excel")
def download_excel(
    request: Request,
    product: str,
    mode: str = "outbound"
):
    db = SessionLocal()

    # =========================
    # 데이터 조회
    # =========================

    if mode == "outbound":

        data = db.query(Outbound)\
            .filter(Outbound.product == product)\
            .all()

    else:

        data = db.query(Inbound)\
            .filter(Inbound.product == product)\
            .all()

    # =========================
    # 엑셀 데이터 생성
    # =========================

    rows = []

    for r in data:

        rows.append({
            "날짜": (
                r.created_at.strftime("%Y-%m-%d")
                if r.created_at else ""
            ),
            "Serial": r.serial,
            "제품": r.product,
            "Size": r.size,
            "출고구분": getattr(r, "category", ""),
            "출고처": getattr(r, "client", ""),
            "비고": getattr(r, "note", "")
        })

    df = pd.DataFrame(rows)

    output = io.BytesIO()

    df.to_excel(
        output,
        index=False
    )

    output.seek(0)

    # =========================
    # 로그 저장
    # =========================

    user = request.session.get(
        "user",
        "unknown"
    )

    service_name = SERVICE_NAMES.get(
        product,
        product
    )

    save_log(
        user=user,
        product=service_name,
        action="DOWNLOAD_EXCEL",
        serial="",
        detail=f"{mode} 엑셀 다운로드"
    )

    db.close()

    # =========================
    # 파일 반환
    # =========================

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            f"attachment; filename={product}_{mode}.xlsx"
        }
    )

@router.get("/download-search-excel")
def download_search_excel(
    request: Request,
    q: str = "",
    status: str = ""
):

    db = SessionLocal()

    outbound = db.query(Outbound)
    inbound = db.query(Inbound)

    if q:

        outbound = outbound.filter(
            Outbound.serial.contains(q)
        )

        inbound = inbound.filter(
            Inbound.serial.contains(q)
        )

    rows = []

    if status in ["", "outbound"]:

        for r in outbound.all():

            rows.append({
                "유형": "출고",
                "날짜": r.created_at.strftime("%Y-%m-%d")
                    if r.created_at else "",
                "Serial": r.serial,
                "Size": r.size,
                "구분": r.category,
                "출고처": r.client,
                "비고": r.note
            })

    if status in ["", "inbound"]:

        for r in inbound.all():

            rows.append({
                "유형": "입고",
                "날짜": r.created_at.strftime("%Y-%m-%d")
                    if r.created_at else "",
                "Serial": r.serial,
                "Size": r.size,
                "구분": r.category,
                "출고처": r.client,
                "비고": r.note
            })

    df = pd.DataFrame(rows)

    output = io.BytesIO()

    df.to_excel(
        output,
        index=False
    )

    output.seek(0)

    user = request.session.get(
        "user",
        "unknown"
    )

    save_log(
        user=user,
        product="통합 검색",
        action="DOWNLOAD_EXCEL",
        serial=q,
        detail=f"status={status}"
    )

    db.close()

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            "attachment; filename=search.xlsx"
        }
    )