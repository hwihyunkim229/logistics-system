import unittest
from datetime import date, timedelta
from types import SimpleNamespace as Row

from app.routers.mrp import calculate_mrp


class MrpShortageDateTests(unittest.TestCase):
    def calculate(self, stock, month=None):
        plans = [Row(product_name='TEST', plan_date=date(2026, 8, 31), plan_qty=10),
                 Row(product_name='TEST', plan_date=date(2026, 9, 10), plan_qty=20)]
        return calculate_mrp(
            None, month=month, all_plans=plans,
            bom_rows=[Row(product_name='TEST', component_code='A', component_name='Material', qty=1)],
            inventory_rows=[Row(item_code='A', warehouse_type='창고재고', grade='A', qty=stock)],
            material_rows=[Row(item_code='A', supplier='Supplier', lead_time_week=2, moq=10)],
            note_rows=[],
        )[1][0]

    def test_sufficient_and_exact_stock_have_no_shortage_dates(self):
        for stock in (30, 40):
            with self.subTest(stock=stock):
                row = self.calculate(stock)
                self.assertEqual(row['status'], 'OK')
                self.assertIsNone(row['need_date'])
                self.assertIsNone(row['order_date'])

    def test_shortage_still_uses_first_shortage_day_and_lead_time(self):
        row = self.calculate(15)
        self.assertEqual(row['need_date'], date(2026, 9, 10))
        self.assertEqual(row['order_date'], date(2026, 9, 10) - timedelta(weeks=2))

    def test_period_deducts_prior_plans_before_deciding_dates(self):
        ready = self.calculate(30, month=9)
        self.assertEqual(ready['stock_qty'], 20)
        self.assertIsNone(ready['need_date'])
        self.assertIsNone(ready['order_date'])
        short = self.calculate(25, month=9)
        self.assertEqual(short['shortage_qty'], 5)
        self.assertEqual(short['need_date'], date(2026, 9, 10))
