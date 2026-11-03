import unittest

from app.assistant.agent import AssistantAgent
from app.assistant.memory import memory
from app.assistant.query_router import resolve_tool


class AssistantPageFollowupTests(unittest.TestCase):
    def tearDown(self):
        memory.clear("page-test")
        memory.clear("inventory-followup")
        memory.clear("clarify-test")
        memory.clear("combined-followup")
        memory.clear("direction-followup")
        memory.clear("lot-context-followup")
        memory.clear("inventory-domain-switch")
        memory.clear("combined-domain-switch")
        memory.clear("mrp-summary-followup")
        memory.clear("domain-change")
        memory.clear("workflow-department-switch")

    def test_mrp_result_followup_keeps_mrp_context(self):
        agent = AssistantAgent(None)
        first = agent.chat("mrp 화면으로 이동해줘", "page-test")
        second = agent.chat("대시보드 말고 result로 이동해줘", "page-test")
        self.assertEqual(first.get("url"), "/mrp")
        self.assertEqual(second.get("url"), "/mrp/result")

    def test_inventory_confirmation_reuses_previous_query(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "inventory-followup",
            "inventory.movement_search",
            {"item": "", "movement_type": "IN", "period": "all", "limit": 1},
        )
        selected = agent._resolve_follow_up("수불재고에서 확인해줘", "inventory-followup")
        self.assertEqual(selected["tool"], "inventory.movement_search")
        self.assertEqual(selected["arguments"]["movement_type"], "IN")

    def test_clarification_answer_selects_original_tool(self):
        agent = AssistantAgent(None)
        memory.save("clarify-test", "assistant.clarification", [
            {"label": "수불 재고", "tool": "inventory.search", "arguments": {"item": ""}},
            {"label": "가계상 재고", "tool": "stock.summary", "arguments": {"item": ""}},
        ])
        selected = agent._resolve_follow_up("2번 가계상 재고", "clarify-test")
        self.assertEqual(selected["tool"], "stock.summary")

    def test_clarification_accepts_short_natural_answers(self):
        agent = AssistantAgent(None)
        choices = [
            {"label": "수불 재고", "tool": "inventory.search", "arguments": {"item": ""}},
            {"label": "가계상 재고", "tool": "stock.summary", "arguments": {"item": ""}},
        ]
        for answer, expected in (("수불", "inventory.search"), ("장부", "stock.summary")):
            with self.subTest(answer=answer):
                self.assertEqual(agent._resolve_clarification(answer, choices)["tool"], expected)

    def test_number_inside_choice_label_is_not_choice_index(self):
        agent = AssistantAgent(None)
        choices = [
            {"label": "최근 21일", "tool": "inventory.movement_search", "arguments": {"period": "last_21_days"}},
            {"label": "11월 21일 하루", "tool": "inventory.movement_search", "arguments": {"period": "date_20261121"}},
        ]
        selected = agent._resolve_clarification("최근 21일", choices)
        self.assertEqual(selected["arguments"]["period"], "last_21_days")

    def test_combined_stock_followup_keeps_domain_and_changes_period(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "combined-followup",
            "stock.combined_movement_search",
            {"movement_type": "IN", "period": "all", "limit": 1},
        )
        selected = agent._resolve_follow_up(
            "그럼 최근 30일 이내 입고 이력 보여줘",
            "combined-followup",
        )
        self.assertEqual(selected["tool"], "stock.combined_movement_search")
        self.assertEqual(selected["arguments"]["period"], "last_30_days")
        self.assertEqual(selected["arguments"]["movement_type"], "IN")
        self.assertEqual(selected["arguments"]["limit"], 15)

    def test_movement_followup_can_switch_direction_without_losing_period(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "direction-followup",
            "inventory.movement_search",
            {"item": "", "movement_type": "IN", "period": "last_30_days", "limit": 15},
        )
        selected = agent._resolve_follow_up("그럼 출고는?", "direction-followup")
        self.assertEqual(selected["tool"], "inventory.movement_search")
        self.assertEqual(selected["arguments"]["period"], "last_30_days")
        self.assertEqual(selected["arguments"]["movement_type"], "OUT")

    def test_lot_question_does_not_reuse_incompatible_combined_context(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "lot-context-followup",
            "stock.combined_movement_search",
            {"movement_type": "IN", "period": "all", "limit": 1},
        )
        selected = agent._resolve_follow_up(
            "최근 입고된 LOT 하나만 알려줘봐",
            "lot-context-followup",
        )
        self.assertIsNone(selected)
        routed = resolve_tool("최근 입고된 LOT 하나만 알려줘봐")
        self.assertEqual(routed["tool"], "inventory.movement_search")
        self.assertEqual(routed["arguments"]["movement_type"], "IN")
        self.assertTrue(routed["arguments"]["require_lot"])
        self.assertEqual(routed["arguments"]["limit"], 1)

    def test_switching_to_inventory_keeps_recent_lot_conditions(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "inventory-domain-switch",
            "inventory.movement_search",
            {"item": "", "warehouse_type": "", "movement_type": "IN", "period": "all", "limit": 1, "require_lot": True},
        )
        selected = agent._resolve_follow_up("수불재고에서 확인해줘", "inventory-domain-switch")
        self.assertEqual(selected["tool"], "inventory.movement_search")
        self.assertEqual(selected["arguments"]["movement_type"], "IN")
        self.assertEqual(selected["arguments"]["limit"], 1)
        self.assertTrue(selected["arguments"]["require_lot"])

    def test_switching_combined_query_to_inventory_keeps_filters(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "combined-domain-switch",
            "stock.combined_movement_search",
            {"movement_type": "OUT", "period": "last_30_days", "limit": 15},
        )
        selected = agent._resolve_follow_up("그럼 수불재고로 봐줘", "combined-domain-switch")
        self.assertEqual(selected["tool"], "inventory.movement_search")
        self.assertEqual(selected["arguments"]["movement_type"], "OUT")
        self.assertEqual(selected["arguments"]["period"], "last_30_days")

    def test_mrp_shortage_quantity_followup_keeps_mrp_context(self):
        agent = AssistantAgent(None)
        memory.save_context("mrp-summary-followup", "mrp.shortage_summary", {"mode": "count"})
        selected = agent._resolve_follow_up("수량을 알려줘", "mrp-summary-followup")
        self.assertEqual(selected["tool"], "mrp.shortage_summary")
        self.assertEqual(selected["arguments"]["mode"], "qty")

    def test_followup_context_is_preserved_across_project_domains(self):
        agent = AssistantAgent(None)
        cases = (
            ("bom.detail", {"item": "CART BP"}, "소요 수량은?", "bom.detail"),
            ("production.plan", {"item": "CART BP", "period": "all"}, "그럼 날짜는?", "production.plan"),
            ("material.master", {"item": "SL-M-1"}, "업체랑 리드타임은?", "material.master"),
            ("item.master", {"item": "SL-M-1"}, "REV도 알려줘", "item.master"),
            ("workflow.search", {"item": "IEM"}, "현재 단계랑 담당 부서는?", "workflow.status"),
            ("rental.summary", {"item": "노트북"}, "수량은?", "rental.summary"),
            ("activity.search", {"item": "CART BP"}, "더 보여줘", "activity.search"),
            ("admin.user_summary", {"item": ""}, "총 몇 명이야?", "admin.user_summary"),
            ("project.upload_help", {"question": "BOM 업로드"}, "선택 컬럼은?", "project.upload_help"),
        )
        for index, (tool, arguments, followup, expected) in enumerate(cases):
            session_id = f"all-domain-followup-{index}"
            memory.save_context(session_id, tool, arguments)
            with self.subTest(tool=tool, followup=followup):
                selected = agent._resolve_follow_up(followup, session_id)
                self.assertEqual(selected["tool"], expected)
            memory.clear(session_id)

    def test_explicit_new_domain_does_not_reuse_old_context(self):
        agent = AssistantAgent(None)
        memory.save_context("domain-change", "bom.detail", {"item": "CART BP"})
        self.assertIsNone(agent._resolve_follow_up("생산계획 수량 알려줘", "domain-change"))

    def test_workflow_department_followup_changes_only_department(self):
        agent = AssistantAgent(None)
        memory.save_context(
            "workflow-department-switch",
            "workflow.status",
            {"item": "", "status": "IN_PROGRESS", "department": "quality", "limit": 15},
        )
        selected = agent._resolve_follow_up("생산팀에 멈춰있는 번호 알려줘", "workflow-department-switch")
        self.assertEqual(selected["tool"], "workflow.status")
        self.assertEqual(selected["arguments"]["status"], "IN_PROGRESS")
        self.assertEqual(selected["arguments"]["department"], "production")
        self.assertEqual(selected["arguments"]["item"], "")


if __name__ == "__main__":
    unittest.main()
