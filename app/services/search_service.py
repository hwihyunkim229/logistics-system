from sqlalchemy import or_, func


def find_item(model, db, keyword):

    keyword = keyword.strip()

    # 1. 품번 정확 조회
    row = (
        db.query(model)
        .filter(
            func.lower(model.item_code)
            == keyword.lower()
        )
        .first()
    )

    if row:
        return {
            "type": "exact",
            "rows": [row]
        }

    # 2. 품명 정확 조회
    row = (
        db.query(model)
        .filter(
            func.lower(model.item_name)
            == keyword.lower()
        )
        .first()
    )

    if row:
        return {
            "type": "exact",
            "rows": [row]
        }

    # 3. 품번 / 품명 포함 조회
    rows = (
        db.query(model)
        .filter(
            or_(
                func.lower(model.item_name).contains(keyword.lower()),
                func.lower(model.item_code).contains(keyword.lower())
            )
        )
        .order_by(model.item_name)
        .all()
    )

    if not rows:

        return {
            "type": "none",
            "rows": []
        }

    return {
        "type": "multiple",
        "rows": rows
    }