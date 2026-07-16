from datetime import date
from io import BytesIO
from math import ceil
import pandas as pd
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Request,
    UploadFile,
)
from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.item_master import ItemMaster
from app.models.rental_category import RentalCategory
from app.models.rental_movement import RentalMovement
from app.models.rental_stock import RentalStock
from app.utils.logger import save_log

router = APIRouter(prefix="/rental")

templates = Jinja2Templates(
    directory="app/templates"
)


HQ = {
    "경영지원본부": [
        "구매/자재/물류팀",
        "디자인팀",
        "인사총무팀",
    ],
    "경영기획본부": [
        "회계팀",
        "IR/자금팀",
    ],
    "대외협력본부": [
        "MA팀",
        "PR팀",
    ],
    "제품개발본부": [
        "제품기획/PM팀",
        "서비스운영팀",
        "서비스기획팀",
        "인허가팀",
        "정보보안팀",
    ],
    "연구개발본부": [
        "연구기획팀",
        "VSP팀",
        "Server팀",
        "Mobile SW팀",
        "HW/FW팀",
        "기구팀",
    ],
    "품질본부": [
        "QA팀",
        "QC팀",
        "SW품질팀",
    ],
    "생산본부": [
        "생산관리팀",
        "생산팀",
    ],
    "사업본부": [
        "사업개발팀",
        "전략마케팅팀",
        "마케팅팀",
    ],
    "과학본부": [
        "임상연구1팀",
        "임상연구2팀",
    ],
}

SIZES = [
    f"{number}호"
    for number in range(7, 14)
]

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def user(request):
    return (
        request.session.get("user")
        or "system"
    )

def xlsx(
    rows,
    filename,
    sheet,
):
    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        pd.DataFrame(rows).to_excel(
            writer,
            index=False,
            sheet_name=sheet,
        )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )

def category_names(
    db: Session,
):
    rows = (
        db.query(RentalCategory)
        .order_by(RentalCategory.id)
        .all()
    )

    return [
        row.name
        for row in rows
    ]

@router.get("")
def index(
    request: Request,
    keyword: str = "",
    category: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    categories = category_names(db)

    if category not in categories:
        category = (
            categories[0]
            if categories
            else ""
        )

    if category:
        query = (
            db.query(RentalStock)
            .filter(
                RentalStock.category
                == category
            )
        )
    else:
        query = (
            db.query(RentalStock)
            .filter(False)
        )

    if keyword:
        query = query.filter(
            or_(
                RentalStock.item_code.contains(
                    keyword
                ),
                RentalStock.item_name.contains(
                    keyword
                ),
            )
        )

    total = query.count()

    items = (
        query
        .order_by(RentalStock.item_code)
        .offset((page - 1) * 50)
        .limit(50)
        .all()
    )

    item_master_rows = (
        db.query(ItemMaster)
        .filter(
            ItemMaster.item_code.isnot(None)
        )
        .order_by(ItemMaster.item_code)
        .all()
    )

    item_master_list = [
        {
            "code": row.item_code,
            "name": row.item_name,
        }
        for row in item_master_rows
    ]

    return templates.TemplateResponse(
        request=request,
        name="rental/index.html",
        context={
            "items": items,
            "keyword": keyword,
            "category": category,
            "categories": categories,
            "item_master_list": item_master_list,
            "page": page,
            "total_pages": max(
                1,
                ceil(total / 50),
            ),
            "headquarters": HQ,
            "sizes": SIZES,
            "today": date.today().isoformat(),
        },
    )

@router.post("/categories")
def add_category(
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    name = " ".join(
        str(
            data.get("name", "")
        ).split()
    )

    if not name:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "분류명을 입력해 주세요."
                ),
            },
            status_code=400,
        )

    if len(name) > 50:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "분류명은 50자 이내로 "
                    "입력해 주세요."
                ),
            },
            status_code=400,
        )

    existing_category = (
        db.query(RentalCategory)
        .filter(
            RentalCategory.name == name
        )
        .first()
    )

    if existing_category:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "이미 등록된 분류입니다."
                ),
            },
            status_code=409,
        )

    db.add(
        RentalCategory(
            name=name
        )
    )

    db.commit()

    return {
        "status": "success",
        "name": name,
    }

@router.post("/items")
def add_item(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    category = str(
        data.get("category", "")
    ).strip()

    item_code = str(
        data.get("item_code", "")
    ).strip()

    item_name = str(
        data.get("item_name", "")
    ).strip()

    try:
        qty = int(
            data.get("qty", 0)
        )
    except (TypeError, ValueError):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "수량은 숫자로 입력해 주세요."
                ),
            },
            status_code=400,
        )

    if category not in category_names(db):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "대여 분류를 확인해 주세요."
                ),
            },
            status_code=400,
        )

    master = (
        db.query(ItemMaster)
        .filter(
            ItemMaster.item_code
            == item_code
        )
        .first()
    )

    if (
        master
        and master.item_name
    ):
        item_name = master.item_name

    if (
        not item_code
        or not item_name
        or qty < 0
    ):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "품목코드, 품명, 수량을 "
                    "올바르게 입력해 주세요."
                ),
            },
            status_code=400,
        )

    existing_item = (
        db.query(RentalStock)
        .filter(
            RentalStock.category
            == category,
            RentalStock.item_code
            == item_code,
        )
        .first()
    )

    if existing_item:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "해당 분류에 이미 등록된 "
                    "품목코드입니다."
                ),
            },
            status_code=409,
        )

    db.add(
        RentalStock(
            category=category,
            item_code=item_code,
            item_name=item_name,
            qty=qty,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "이미 등록된 품목코드입니다."
                ),
            },
            status_code=409,
        )

    save_log(
        user=user(request),
        product="대여 관리",
        action="RENTAL_ITEM_CREATE",
        serial=item_code,
        detail=(
            f"{category} 신규 품목 등록: "
            f"{item_name} / {qty} EA"
        ),
    )

    return {
        "status": "success"
    }


@router.patch(
    "/items/{item_id}/qty"
)
def update_item_qty(
    item_id: int,
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    raw_qty = str(
        data.get("qty", "")
    ).strip()

    if not raw_qty.isdigit():
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "수량은 0 이상의 정수로 "
                    "입력해 주세요."
                ),
            },
            status_code=400,
        )

    qty = int(raw_qty)

    item = db.get(
        RentalStock,
        item_id,
    )

    if not item:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "대여 재고를 찾을 수 없습니다."
                ),
            },
            status_code=404,
        )

    old_qty = item.qty

    item.qty = qty

    db.commit()

    save_log(
        user=user(request),
        product="대여 관리",
        action="RENTAL_QTY_UPDATE",
        serial=item.item_code,
        detail=(
            f"{item.category} 수량 변경: "
            f"{old_qty} → {qty} EA"
        ),
    )

    return {
        "status": "success",
        "qty": qty,
    }


@router.post("/upload-excel")
async def upload(
    request: Request,
    category: str = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    categories = category_names(db)

    if category not in categories:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "대여 분류를 확인해 주세요."
                ),
            },
            status_code=400,
        )

    try:
        contents = await file.read()

        frame = pd.read_excel(
            BytesIO(contents)
        ).fillna("")
    except Exception:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "엑셀 파일을 읽을 수 없습니다."
                ),
            },
            status_code=400,
        )

    columns = {
        str(column)
        .strip()
        .replace(" ", ""): column
        for column in frame.columns
    }

    required_columns = (
        "품목코드",
        "품명",
        "수량",
    )

    if not all(
        column in columns
        for column in required_columns
    ):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "품목코드, 품명, 수량 "
                    "컬럼이 필요합니다."
                ),
            },
            status_code=400,
        )

    count = 0

    try:
        for _, excel_row in frame.iterrows():
            code = str(
                excel_row[
                    columns["품목코드"]
                ]
            ).strip()

            name = str(
                excel_row[
                    columns["품명"]
                ]
            ).strip()

            if (
                not code
                or not name
            ):
                continue

            qty = int(
                float(
                    excel_row[
                        columns["수량"]
                    ]
                    or 0
                )
            )

            row = (
                db.query(RentalStock)
                .filter_by(
                    item_code=code,
                    category=category,
                )
                .first()
            )

            if row:
                row.item_name = name
                row.qty = qty
            else:
                db.add(
                    RentalStock(
                        item_code=code,
                        item_name=name,
                        category=category,
                        qty=qty,
                    )
                )

            count += 1

        db.commit()

    except (ValueError, TypeError):
        db.rollback()

        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "수량은 숫자로 입력해 주세요."
                ),
            },
            status_code=400,
        )

    save_log(
        user=user(request),
        product="대여 관리",
        action="RENTAL_UPLOAD_EXCEL",
        detail=(
            f"대여 재고 업로드: "
            f"{count}건"
        ),
    )

    return {
        "status": "success",
        "count": count,
    }


@router.get("/download-excel")
def stock_excel(
    request: Request,
    category: str = "",
    db: Session = Depends(get_db),
):
    categories = category_names(db)

    if category not in categories:
        if not categories:
            return JSONResponse(
                {
                    "status": "error",
                    "message": (
                        "먼저 대여 분류를 "
                        "추가해 주세요."
                    ),
                },
                status_code=400,
            )

        category = categories[0]

    rows = (
        db.query(RentalStock)
        .filter(
            RentalStock.category
            == category
        )
        .order_by(RentalStock.item_code)
        .all()
    )

    save_log(
        user=user(request),
        product="대여 관리",
        action="RENTAL_DOWNLOAD_EXCEL",
        detail=(
            f"{category} 대여 재고 다운로드: "
            f"{len(rows)}건"
        ),
    )

    excel_rows = [
        {
            "품목코드": row.item_code,
            "품명": row.item_name,
            "수량": row.qty,
        }
        for row in rows
    ]

    return xlsx(
        excel_rows,
        "rental_stock.xlsx",
        "대여 재고",
    )


@router.post("/move-out")
def move_out(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    try:
        ids = list(
            {
                int(item_id)
                for item_id in data.get(
                    "ids",
                    [],
                )
            }
        )

        qty = int(
            data.get("qty", 1)
        )

        issued = date.fromisoformat(
            data.get(
                "issue_date",
                "",
            )
        )

    except (ValueError, TypeError):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "수량과 불출 일자를 "
                    "확인해 주세요."
                ),
            },
            status_code=400,
        )

    headquarters = data.get(
        "headquarters",
        "",
    )

    department = data.get(
        "department",
        "",
    )

    requester = data.get(
        "requester",
        "",
    ).strip()

    serial_number = data.get(
        "serial_number",
        "",
    ).strip()

    size = data.get("size")

    if (
        not ids
        or qty < 1
        or headquarters not in HQ
        or department
        not in HQ[headquarters]
        or size not in SIZES
        or not requester
        or not serial_number
    ):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "필수 항목을 모두 올바르게 "
                    "입력해 주세요."
                ),
            },
            status_code=400,
        )

    items = (
        db.query(RentalStock)
        .filter(
            RentalStock.id.in_(ids)
        )
        .all()
    )

    if len(items) != len(ids):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "선택 품목을 찾을 수 없습니다."
                ),
            },
            status_code=404,
        )

    short_item = next(
        (
            item
            for item in items
            if item.qty < qty
        ),
        None,
    )

    if short_item:
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    f"{short_item.item_code} "
                    "재고가 부족합니다."
                ),
            },
            status_code=400,
        )

    remark = data.get(
        "remark",
        "",
    ).strip()

    username = user(request)

    for item in items:
        item.qty -= qty

        db.add(
            RentalMovement(
                movement_type="OUT",
                item_code=item.item_code,
                item_name=item.item_name,
                category=item.category,
                qty=qty,
                headquarters=headquarters,
                department=department,
                requester=requester,
                size=size,
                serial_number=serial_number,
                issue_date=issued,
                remark=remark,
                user=username,
            )
        )

    db.commit()

    save_log(
        user=username,
        product="대여 관리",
        action="RENTAL_MOVE_OUT",
        serial=", ".join(
            item.item_code
            for item in items
        ),
        detail=(
            f"대여 재고 출고: "
            f"{len(items)}개 품목 × {qty}"
        ),
    )

    return {
        "status": "success"
    }


@router.get("/history")
def history(
    request: Request,
    keyword: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    query = db.query(
        RentalMovement
    )

    if keyword:
        query = query.filter(
            or_(
                RentalMovement.item_code.contains(
                    keyword
                ),
                RentalMovement.item_name.contains(
                    keyword
                ),
                RentalMovement.requester.contains(
                    keyword
                ),
                RentalMovement.serial_number.contains(
                    keyword
                ),
                RentalMovement.headquarters.contains(
                    keyword
                ),
                RentalMovement.department.contains(
                    keyword
                ),
            )
        )

    total = query.count()

    rows = (
        query
        .order_by(
            RentalMovement.issue_date.desc(),
            RentalMovement.id.desc(),
        )
        .offset((page - 1) * 50)
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="rental/history.html",
        context={
            "history": rows,
            "keyword": keyword,
            "page": page,
            "total_pages": max(
                1,
                ceil(total / 50),
            ),
        },
    )


@router.patch("/history/{row_id}")
def edit(
    row_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    row = db.get(
        RentalMovement,
        row_id,
    )

    field = data.get("field")

    if (
        not row
        or field
        not in {
            "remark",
            "requester",
        }
    ):
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    "수정할 수 없습니다."
                ),
            },
            status_code=400,
        )

    setattr(
        row,
        field,
        str(
            data.get("value", "")
        ).strip(),
    )

    db.commit()

    return {
        "status": "success"
    }


@router.get(
    "/history/download-excel"
)
def history_excel(
    request: Request,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(RentalMovement)
        .order_by(
            RentalMovement.issue_date.desc(),
            RentalMovement.id.desc(),
        )
        .all()
    )

    save_log(
        user=user(request),
        product="대여 관리",
        action=(
            "RENTAL_HISTORY_DOWNLOAD_EXCEL"
        ),
        detail=(
            f"대여 입출고 다운로드: "
            f"{len(rows)}건"
        ),
    )

    excel_rows = [
        {
            "본부": row.headquarters,
            "부서": row.department,
            "품목코드": row.item_code,
            "품명": row.item_name,
            "요청자": row.requester,
            "사이즈": row.size,
            "S/N": row.serial_number,
            "불출일자": (
                row.issue_date.isoformat()
            ),
            "비고": row.remark,
        }
        for row in rows
    ]

    return xlsx(
        excel_rows,
        "rental_movement_history.xlsx",
        "대여 입출고 현황",
    )