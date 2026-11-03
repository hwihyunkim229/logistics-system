import unittest

from app.assistant.agent import AssistantAgent
from app.assistant.memory import memory
from app.assistant.query_router import resolve_tool


class AssistantEdgeCaseTests(unittest.TestCase):
    def tearDown(self):
        memory.clear("invalid-choice")

    def test_empty_and_noise_inputs_do_not_crash(self):
        for question in (None, "", "   ", "???ㅋㅋㅠㅠ", "...!!!"):
            with self.subTest(question=question):
                self.assertEqual(resolve_tool(question)["tool"], "general.chat")

    def test_mixed_domains_request_clarification(self):
        for question in (
            "수불재고랑 가계상재고 둘 다 보여줘",
            "BOM하고 생산계획 알려줘",
            "MRP 및 BOM 조회",
        ):
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "assistant.clarify")
                self.assertGreaterEqual(len(result["arguments"]["choices"]), 2)

    def test_malgo_uses_the_domain_after_malgo(self):
        self.assertEqual(resolve_tool("가계상 말고 수불재고 보여줘")["tool"], "inventory.search")
        self.assertEqual(resolve_tool("수불재고 말고 가계상재고 보여줘")["tool"], "stock.summary")

    def test_invalid_calendar_date_returns_clear_message(self):
        result = resolve_tool("2026년 2월 30일 수불재고 입출고 보여줘")
        self.assertEqual(result["tool"], "assistant.invalid_request")
        self.assertIn("유효한 날짜가 아닙니다", result["arguments"]["message"])

    def test_invalid_clarification_answer_keeps_choices(self):
        agent = AssistantAgent(None)
        choices = [
            {"label": "수불 재고", "tool": "inventory.search", "arguments": {"item": ""}},
            {"label": "가계상 재고", "tool": "stock.summary", "arguments": {"item": ""}},
        ]
        memory.save("invalid-choice", "assistant.clarification", choices)
        selected = agent._resolve_follow_up("99번", "invalid-choice")
        self.assertEqual(selected["tool"], "assistant.clarify")
        self.assertEqual(selected["arguments"]["choices"], choices)

    def test_sql_like_text_is_only_a_search_keyword(self):
        result = resolve_tool("품목 '; DROP TABLE stock;--' 조회")
        self.assertIn(result["tool"], {"item.master", "global.search"})


if __name__ == "__main__":
    unittest.main()
