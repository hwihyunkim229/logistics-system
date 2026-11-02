import unittest

from app.assistant.query_router import resolve_tool


class AssistantRoutingTests(unittest.TestCase):
    def test_capability_question_is_not_treated_as_data_search(self):
        result = resolve_tool("이 시스템에서 뭘 할 수 있어?")
        self.assertEqual(result["tool"], "assistant.capabilities")

    def test_natural_identity_questions_are_not_data_searches(self):
        for question in (
            "넌 뭐하는 애야?", "너는 누구야?", "무슨 일 해?",
            "정체가 뭐야?", "어떤 도우미야?", "네 역할이 뭐야?",
        ):
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "assistant.capabilities")

    def test_greeting_is_conversation_not_global_search(self):
        self.assertEqual(resolve_tool("안녕 반가워")["tool"], "general.chat")

    def test_inventory_lot_is_inferred_without_lot_word(self):
        result = resolve_tool("수불 재고 F25 A등급 수량 알려줘")
        self.assertEqual(result["tool"], "inventory.search")
        self.assertEqual(result["arguments"]["lot"], "F25")
        self.assertEqual(result["arguments"]["grade"], "A")
        self.assertEqual(result["arguments"]["item"], "")

    def test_explicit_lot_still_works(self):
        result = resolve_tool("수불 재고 LOT G23 B등급 조회")
        self.assertEqual(result["arguments"]["lot"], "G23")
        self.assertEqual(result["arguments"]["grade"], "B")

    def test_causal_question_is_not_misrepresented_as_count(self):
        result = resolve_tool("이번 달 입고가 왜 줄었어?")
        self.assertEqual(result["tool"], "assistant.analysis_limit")

    def test_cross_domain_calculation_is_not_sent_to_stock_lookup(self):
        result = resolve_tool("BOM이랑 재고 기준으로 생산 가능한 수량 알려줘")
        self.assertEqual(result["tool"], "assistant.analysis_limit")

    def test_supported_mrp_question_keeps_deterministic_route(self):
        result = resolve_tool("MRP 부족 품목 상위 5개 보여줘")
        self.assertEqual(result["tool"], "mrp.shortage_search")
        self.assertEqual(result["arguments"]["limit"], 5)

    def test_korean_sentence_ending_is_not_used_as_item_keyword(self):
        result = resolve_tool("수불재고 원자재 총 몇개야?")
        self.assertEqual(result["tool"], "inventory.search")
        self.assertEqual(result["arguments"]["category"], "원자재")
        self.assertEqual(result["arguments"]["item"], "")

    def test_excel_question_uses_project_knowledge(self):
        result = resolve_tool("수불 재고 엑셀 업로드 필수 행이 뭐야?")
        self.assertEqual(result["tool"], "project.upload_help")

    def test_generic_material_noun_is_inventory_scope_not_item_name(self):
        result = resolve_tool("창고재고에 자재 몇개있어?")
        self.assertEqual(result["tool"], "inventory.search")
        self.assertEqual(result["arguments"]["warehouse_type"], "창고재고")
        self.assertEqual(result["arguments"]["category"], "원자재")
        self.assertEqual(result["arguments"]["item"], "")

    def test_generic_inventory_noun_is_not_item_name(self):
        result = resolve_tool("외주재고에 품목 몇 개 있어?")
        self.assertEqual(result["tool"], "inventory.search")
        self.assertEqual(result["arguments"]["warehouse_type"], "외주재고")
        self.assertEqual(result["arguments"]["item"], "")

    def test_workflow_number_question_routes_to_workflow_data(self):
        result = resolve_tool("지금 cart platform iem에 부여된 workflow 번호 알려줘")
        self.assertEqual(result["tool"], "workflow.search")
        self.assertEqual(result["arguments"]["service_type"], "cart_platform")
        self.assertEqual(result["arguments"]["item"].lower(), "iem")

    def test_generic_workflow_find_lists_recent_workflows(self):
        result = resolve_tool("Workflow 번호 찾기")
        self.assertEqual(result["tool"], "workflow.search")
        self.assertEqual(result["arguments"]["item"], "")

    def test_inventory_lot_overview_uses_lot_summary(self):
        result = resolve_tool("수불재고 LOT 현황 알려줘")
        self.assertEqual(result["tool"], "inventory.lot_summary")

    def test_result_page_phrase_routes_to_mrp_result(self):
        result = resolve_tool("대시보드 말고 result로 이동해줘")
        self.assertEqual(result["tool"], "page.move")
        self.assertEqual(result["arguments"]["page"], "mrp_result")

    def test_shortage_material_phrases_use_mrp_results(self):
        for question in ("부족자재 알려줘", "mrp 부족 자재 알려줘", "부족한 품목 보여줘"):
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "mrp.shortage_search")
                self.assertEqual(result["arguments"]["limit"], 5)

    def test_products_with_production_plan_do_not_route_to_stock(self):
        result = resolve_tool("생산 계획 있는 제품 알려줘")
        self.assertEqual(result["tool"], "production.products")
        self.assertEqual(result["arguments"]["period"], "all")

    def test_inventory_movement_history_does_not_search_for_word_history(self):
        result = resolve_tool("수불 재고 입출고 내역 보여줘")
        self.assertEqual(result["tool"], "inventory.movement_search")
        self.assertEqual(result["arguments"]["item"], "")
        self.assertEqual(result["arguments"]["movement_type"], "")


if __name__ == "__main__":
    unittest.main()
