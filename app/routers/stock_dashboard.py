from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
from sqlalchemy import func
from app.database import SessionLocal
from app.models.stock import Stock
from app.models.stock_movement import StockMovement
from sqlalchemy import distinct

router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)


def get_sub_category(item_name):

    name = item_name.upper()

    if "RING" in name:
        return "RING"

    elif "CRADLE" in name:
        return "CRADLE"

    return "기타"

def get_raw_category(item_name):

    name = item_name.upper()

    if "PBA" in name:
        return "PBA"

    elif "INNER" in name:
        return "INNER"

    elif "OUTER" in name:
        return "OUTER"

    elif "TOP" in name:
        return "TOP COVER"

    return "사급자재"


@router.get("/stock/dashboard")
def stock_dashboard(
    request: Request,
    start: Optional[str] = None,
    end: Optional[str] = None
):

    db = SessionLocal()

    today = datetime.today().date()

    total_items = db.query(
        func.count(
            distinct(
                Stock.item_code
            )
        )
    ).scalar()

    total_qty = db.query(
        func.sum(Stock.qty)
    ).scalar() or 0

    today_in = db.query(
        func.sum(StockMovement.qty)
    ).filter(
        StockMovement.movement_type == "IN"
    ).scalar() or 0

    today_out = db.query(
        func.sum(StockMovement.qty)
    ).filter(
        StockMovement.movement_type == "OUT"
    ).scalar() or 0

    category_labels = []
    category_qtys = []

    for category in [
        "반제품",
        "제품",
        "원자재"
    ]:

        qty = db.query(
            func.sum(Stock.qty)
        ).filter(
            Stock.category == category
        ).scalar() or 0

        category_labels.append(category)
        category_qtys.append(qty)

    raw_items = db.query(
        Stock
    ).filter(
        Stock.category == "원자재"
    ).all()

    semi_data = {
        "RING": 0,
        "CRADLE": 0
    }

    semi_items = db.query(
        Stock
    ).filter(
        Stock.category == "반제품"
    ).all()

    for item in semi_items:

        sub = get_sub_category(
            item.item_name
        )

        if sub in semi_data:
            semi_data[sub] += item.qty

    raw_data = {
        "INNER":0,
        "OUTER":0,
        "TOP COVER":0,
        "PBA":0,
        "사급자재":0
    }

    def get_raw_category(item_name):

        name = item_name.upper()

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

    raw_items = db.query(
        Stock
    ).filter(
        Stock.category == "원자재"
    ).all()

    for item in raw_items:

        sub = get_raw_category(
            item.item_name
        )

        raw_data[sub] += item.qty

    movement_chart = {
        "반제품": {
            "IN": 0,
            "OUT": 0
        },
        "제품": {
            "IN": 0,
            "OUT": 0
        },
        "원자재": {
            "IN": 0,
            "OUT": 0
        }
    }

    movement_query = db.query(
        StockMovement
    )

    if start and end:

        start_date = datetime.strptime(
            start,
            "%Y-%m-%d"
        )

        end_date = datetime.strptime(
            end,
            "%Y-%m-%d"
        )

        movement_query = movement_query.filter(
            StockMovement.created_at >= start_date,
            StockMovement.created_at <= end_date
        )

    movements = movement_query.all()

    for move in movements:

        category = move.category
        movement_type = move.movement_type

        if (
            category in movement_chart
            and movement_type in ["IN", "OUT"]
        ):
            movement_chart[
                category
            ][movement_type] += move.qty
            

    db.close()

    return templates.TemplateResponse(
        request=request,
        name="stock/dashboard.html",
        context={

            "total_items": total_items,
            "total_qty": total_qty,
            "today_in": today_in,
            "today_out": today_out,
            "start": start,
            "end": end,
            "category_labels": category_labels,
            "category_qtys": category_qtys,
            "semi_labels": list(
                semi_data.keys()
            ),
            "semi_qtys": list(
                semi_data.values()
            ),

            "raw_labels": list(
                raw_data.keys()
            ),
            "raw_qtys": list(
                raw_data.values()
            ),
            "movement_labels": [
                "반제품",
                "제품",
                "원자재"
            ],

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