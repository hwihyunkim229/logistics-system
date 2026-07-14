from sqlalchemy import or_, func

def find_item(model, db, keyword):

    keyword = keyword.strip()

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