from sqlalchemy import inspect, text


MOVEMENT_COLUMNS = {
    "lot": "VARCHAR",
    "inspector": "VARCHAR",
    "first_received_date": "DATE",
    "grade": "VARCHAR",
    "request_id": "VARCHAR",
    "set_name": "VARCHAR",
    "set_component": "VARCHAR",
    "set_count": "INTEGER",
}


def ensure_stock_schema(engine):
    inspector = inspect(engine)
    if not inspector.has_table("stock_movement"):
        return
    existing = {column["name"] for column in inspector.get_columns("stock_movement")}
    with engine.begin() as connection:
        for column, column_type in MOVEMENT_COLUMNS.items():
            if column not in existing:
                connection.execute(text(f"ALTER TABLE stock_movement ADD COLUMN {column} {column_type}"))
