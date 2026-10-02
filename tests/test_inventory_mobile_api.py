import asyncio
import unittest
from unittest.mock import patch

from fastapi import Request
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.routers.inventory import (
    InventoryMovementRequest,
    inventory_mobile_items,
    inventory_move_in,
    inventory_move_out,
)


def request_with_session():
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/inventory/mobile/items",
            "headers": [],
            "session": {"user": "mobile-user"},
        }
    )


class InventoryMobileApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            engine,
            tables=[Inventory.__table__, InventoryMovement.__table__],
        )
        self.db = sessionmaker(bind=engine)()
        self.item = Inventory(
            item_code="ITEM-001",
            item_name="테스트 품목",
            category="원자재",
            warehouse_type="창고재고",
            lot="LOT-01",
            grade="A",
            rev="R1",
            qty=10,
        )
        self.db.add(self.item)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_movement_request_rejects_zero_or_empty_values(self):
        with self.assertRaises(ValidationError):
            InventoryMovementRequest(ids=[], qty=1)
        with self.assertRaises(ValidationError):
            InventoryMovementRequest(ids=[self.item.id], qty=0)

    def test_mobile_item_search_returns_inventory_id_and_fields(self):
        result = inventory_mobile_items(
            request_with_session(),
            item_code="ITEM-001",
            lot="LOT-01",
            warehouse_type="창고재고",
            keyword="",
            limit=50,
            db=self.db,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["user"], "mobile-user")
        self.assertEqual(result["items"][0]["id"], self.item.id)
        self.assertEqual(result["items"][0]["qty"], 10)

    @patch("app.routers.inventory.save_log")
    def test_move_in_and_out_update_stock_and_history(self, _save_log):
        asyncio.run(
            inventory_move_in(
                request_with_session(),
                InventoryMovementRequest(
                    ids=[self.item.id],
                    qty=3,
                    remark="APK",
                    lot="LOT-QR-01",
                    inspector="홍길동",
                    first_received_date="2026/10/02",
                ),
                self.db,
            )
        )
        self.db.refresh(self.item)
        self.assertEqual(self.item.qty, 13)
        inbound_history = self.db.query(InventoryMovement).first()
        self.assertEqual(inbound_history.item_name, "테스트 품목")
        self.assertEqual(inbound_history.lot, "LOT-QR-01")
        self.assertEqual(inbound_history.inspector, "홍길동")
        self.assertEqual(inbound_history.first_received_date.isoformat(), "2026-10-02")
        self.assertEqual(self.item.lot, "LOT-01")

        asyncio.run(
            inventory_move_out(
                request_with_session(),
                InventoryMovementRequest(ids=[self.item.id], qty=2, remark="APK"),
                self.db,
            )
        )
        self.db.refresh(self.item)
        self.assertEqual(self.item.qty, 11)
        self.assertEqual(self.db.query(InventoryMovement).count(), 2)


if __name__ == "__main__":
    unittest.main()
