from sqlalchemy import inspect, text

def ensure_rental_schema(engine):
    """Add rental category columns for databases created before this feature."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in ("rental_stock", "rental_movement"):
            if table not in inspector.get_table_names():
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "category" not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN category VARCHAR"))