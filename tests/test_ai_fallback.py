import os
import unittest
from unittest.mock import patch

from app.ai.responder import make_answer


class AiFallbackTests(unittest.TestCase):
    def test_structured_database_answer_does_not_call_ai_by_default(self):
        result = {
            "status": "rows",
            "domain": "inventory_movement",
            "rows": [{
                "created_at": "2026-11-03 09:00",
                "item_code": "TEST-1",
                "item_name": "테스트 품목",
                "warehouse_type": "창고재고",
                "movement_type": "IN",
                "qty": 3,
                "lot": "L1",
                "user": "tester",
            }],
        }
        with patch.dict(os.environ, {"AI_ENHANCE_STRUCTURED_ANSWERS": "0"}), patch(
            "app.ai.responder.ask_ai"
        ) as ask_ai:
            answer = make_answer("최근 입고 알려줘", result)

        ask_ai.assert_not_called()
        self.assertIn("테스트 품목", answer)
        self.assertIn("LOT L1", answer)
        self.assertIn("입고 3 EA", answer)

    def test_single_recent_result_has_accurate_truncation_message(self):
        result = {
            "status": "rows",
            "domain": "inventory_movement",
            "truncated": True,
            "requested_limit": 1,
            "rows": [{
                "created_at": "2026-11-03 15:34",
                "item_code": "TEST-1",
                "item_name": "테스트 품목",
                "warehouse_type": "창고재고",
                "movement_type": "OUT",
                "qty": 1,
                "lot": "",
                "user": "tester",
            }],
        }
        answer = make_answer("최근 입출고 알려줘", result)
        self.assertIn("가장 최근 입출고 1건만 표시했습니다", answer)
        self.assertNotIn("결과가 많아", answer)
        self.assertIn("출고 1 EA", answer)

    def test_combined_recent_result_uses_same_limit_message_and_labels(self):
        result = {
            "status": "rows", "domain": "combined_stock_movement",
            "truncated": True, "requested_limit": 1,
            "rows": [{"stock_type": "가계상 재고", "created_at": "2026-11-03 15:33",
                      "item_name": "테스트", "item_code": "T-1", "movement_type": "IN", "qty": 30}],
        }
        answer = make_answer("최근 입고 품명", result)
        self.assertIn("입고 30 EA", answer)
        self.assertIn("가장 최근 입출고 1건만 표시했습니다", answer)
        self.assertNotIn("결과가 많아", answer)

    def test_smalltalk_is_fully_local(self):
        with patch("app.ai.responder.ask_ai") as ask_ai:
            answer = make_answer("안녕", {"status": "smalltalk", "message": "안녕하세요."})
        ask_ai.assert_not_called()
        self.assertEqual(answer, "안녕하세요.")


if __name__ == "__main__":
    unittest.main()
