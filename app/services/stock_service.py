from app.models.stock import Stock
from app.services.search_service import find_item
from app.assistant.registry import tool


@tool("stock.book")
def get_book_stock(db, item: str):

    result = find_item(
        Stock,
        db,
        item
    )

    # 검색 결과 없음
    if result["type"] == "none":

        return {
            "status": "none"
        }

    # 여러 개 검색
    if result["type"] == "multiple":

        return {

            "status": "multiple",

            "items": [

                {
                    "item_code": row.item_code,
                    "item_name": row.item_name
                }

                for row in result["rows"]

            ]

        }

    # 정확히 하나
    row = result["rows"][0]

    return {

        "status": "exact",

        "item_code": row.item_code,

        "item_name": row.item_name,

        "category": row.category,

        "grade": row.grade,

        "rev": row.rev,

        "qty": row.qty

    }