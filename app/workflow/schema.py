from sqlalchemy import inspect, text

PURCHASE_COLUMNS = {
    "purchase_item_code": "VARCHAR",
    "purchase_item_name": "VARCHAR",
    "purchase_lot": "VARCHAR",
}

REMNANT_COLUMNS = {
    "source_warehouse": "VARCHAR",
    "transfer_status": "VARCHAR",
}

def ensure_workflow_schema(engine):
    inspector = inspect(engine)

    if not inspector.has_table("workflow_items"):
        return

    existing = {
        column["name"]
        for column in inspector.get_columns("workflow_items")
    }

    with engine.begin() as conn:
        for column, column_type in PURCHASE_COLUMNS.items():
            if column not in existing:
                conn.execute(
                    text(
                        f"ALTER TABLE workflow_items "
                        f"ADD COLUMN {column} {column_type}"
                    )
                )

        conn.execute(
            text(
                """
                UPDATE workflow_items
                SET
                    purchase_item_code = COALESCE(
                        purchase_item_code,
                        prev_item_code,
                        item_code
                    ),
                    purchase_item_name = COALESCE(
                        purchase_item_name,
                        prev_item_name,
                        item_name
                    ),
                    purchase_lot = COALESCE(
                        purchase_lot,
                        prev_lot,
                        lot
                    )
                WHERE purchase_item_code IS NULL
                   OR purchase_item_name IS NULL
                   OR purchase_lot IS NULL
                """
            )
        )

        conn.execute(
            text(
                """
                UPDATE workflow_items
                SET received_at = COALESCE(created_at, CURRENT_TIMESTAMP)
                WHERE received_at IS NULL
                """
            )
        )

    if not inspector.has_table("workflow_remnants"):
        return

    remnant_columns = {
        column["name"]
        for column in inspector.get_columns("workflow_remnants")
    }
    with engine.begin() as conn:
        for column, column_type in REMNANT_COLUMNS.items():
            if column not in remnant_columns:
                conn.execute(
                    text(
                        f"ALTER TABLE workflow_remnants "
                        f"ADD COLUMN {column} {column_type}"
                    )
                )
        conn.execute(
            text(
                """
                UPDATE workflow_remnants
                SET transfer_status = COALESCE(transfer_status, 'AVAILABLE')
                WHERE transfer_status IS NULL
                """
            )
        )