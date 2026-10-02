from sqlalchemy import inspect, text


MOVEMENT_COLUMNS = {
    "lot": "VARCHAR",
    "inspector": "VARCHAR",
    "first_received_date": "DATE",
}


def ensure_inventory_schema(engine):
    """Add QR traceability fields without splitting raw-material stock by LOT."""
    inspector = inspect(engine)
    if not inspector.has_table("inventory_movement"):
        return

    existing = {column["name"] for column in inspector.get_columns("inventory_movement")}
    with engine.begin() as connection:
        for column, column_type in MOVEMENT_COLUMNS.items():
            if column not in existing:
                connection.execute(
                    text(f"ALTER TABLE inventory_movement ADD COLUMN {column} {column_type}")
                )
