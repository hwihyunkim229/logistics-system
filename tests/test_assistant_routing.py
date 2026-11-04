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
        self.assertEqual(resolve_tool("안녕 반가워")["tool"], "assistant.smalltalk")

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

        result = resolve_tool("workflow 번호 좀 알려줘")
        self.assertEqual(result["tool"], "workflow.search")
        self.assertEqual(result["arguments"]["item"], "")

    def test_workflow_item_extraction_removes_request_fillers_and_particles(self):
        result = resolve_tool("cart platform iem에 workflow 번호 목록 알려줘")
        self.assertEqual(result["tool"], "workflow.search")
        self.assertEqual(result["arguments"]["service_type"], "cart_platform")
        self.assertEqual(result["arguments"]["item"].lower(), "iem")

    def test_workflow_in_progress_department_filter(self):
        result = resolve_tool("지금 워크플로우 진행되고 있는 것 중에 품질팀에 멈춰있는 번호 알려줘")
        self.assertEqual(result["tool"], "workflow.status")
        self.assertEqual(result["arguments"]["status"], "IN_PROGRESS")
        self.assertEqual(result["arguments"]["department"], "quality")
        self.assertEqual(result["arguments"]["item"], "")

    def test_standalone_department_stalled_question_is_workflow(self):
        cases = (
            ("품질팀 대기중인 번호", "quality"),
            ("자재팀에 진행 중인 건 번호 보여줘", "material"),
            ("구매팀에서 머물러있는 번호", "purchase"),
        )
        for question, department in cases:
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "workflow.status")
                self.assertEqual(result["arguments"]["department"], department)
                self.assertEqual(result["arguments"]["status"], "IN_PROGRESS")
                self.assertEqual(result["arguments"]["item"], "")

        ambiguous = resolve_tool("생산팀에 멈춰있는 번호 알려줘")
        self.assertEqual(ambiguous["tool"], "assistant.clarify")
        self.assertEqual(len(ambiguous["arguments"]["choices"]), 2)
        self.assertEqual(ambiguous["arguments"]["choices"][0]["tool"], "workflow.status")
        self.assertEqual(ambiguous["arguments"]["choices"][1]["tool"], "production.plan")

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

    def test_mrp_shortage_count_and_quantity_are_not_top_five_lists(self):
        count = resolve_tool("mrp 부족 자재 총 몇 개야?")
        self.assertEqual(count["tool"], "mrp.shortage_summary")
        self.assertEqual(count["arguments"]["mode"], "count")

        qty = resolve_tool("MRP 부족 자재 총수량 알려줘")
        self.assertEqual(qty["tool"], "mrp.shortage_summary")
        self.assertEqual(qty["arguments"]["mode"], "qty")

    def test_products_with_production_plan_do_not_route_to_stock(self):
        result = resolve_tool("생산 계획 있는 제품 알려줘")
        self.assertEqual(result["tool"], "production.products")
        self.assertEqual(result["arguments"]["period"], "all")

    def test_inventory_movement_history_does_not_search_for_word_history(self):
        result = resolve_tool("수불 재고 입출고 내역 보여줘")
        self.assertEqual(result["tool"], "inventory.movement_search")
        self.assertEqual(result["arguments"]["item"], "")
        self.assertEqual(result["arguments"]["movement_type"], "")

    def test_screenshot_recent_inventory_questions(self):
        result = resolve_tool("수불재고 입출고현황에서 최근 입고 또는 출고된 품명 알려줘")
        self.assertEqual(result["tool"], "inventory.movement_search")
        self.assertEqual(result["arguments"]["limit"], 1)
        self.assertEqual(result["arguments"]["item"], "")

    def test_rolling_period_inventory_questions(self):
        cases = (
            ("최근 한 달 동안 수불재고 입출고 내역 알려줘", "last_1_months"),
            ("수불재고 최근 36일 입출고 현황", "last_36_days"),
            ("지난 2주 수불재고 입출고 내역", "last_2_weeks"),
            ("지난달 수불재고 입출고 내역", "previous_month"),
        )
        for question, period in cases:
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "inventory.movement_search")
                self.assertEqual(result["arguments"]["period"], period)
                self.assertEqual(result["arguments"].get("limit", 15), 15)
                self.assertEqual(result["arguments"].get("item", ""), "")

    def test_more_period_writing_styles(self):
        cases = (
            ("수불재고 21일간 입출고", "last_21_days"),
            ("수불재고 21일 전부터 입출고 내역", "last_21_days"),
            ("수불재고 한달간 입출고", "last_1_months"),
            ("지난주 수불재고 입출고", "previous_week"),
            ("금주 수불재고 입출고", "this_week"),
            ("금월 수불재고 입출고", "this_month"),
            ("10월 1일부터 10월 20일까지 수불재고 입출고", "range_20261001_20261020"),
            ("2026년 10월 21일 수불재고 입출고", "date_20261021"),
        )
        for question, period in cases:
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "inventory.movement_search")
                self.assertEqual(result["arguments"]["period"], period)
                self.assertEqual(result["arguments"].get("item", ""), "")

    def test_bare_day_number_requests_clarification(self):
        result = resolve_tool("수불재고 21일 입출고 내역")
        self.assertEqual(result["tool"], "assistant.clarify")
        self.assertIn("기간인가요, 날짜인가요", result["arguments"]["prompt"])

    def test_previously_uncovered_project_domains(self):
        cases = (
            ("대여재고 뭐 있어?", "rental.summary", ""),
            ("최근 21일 대여 출고 내역", "rental.movement_search", ""),
            ("CART BP workflow 지금 어느 단계야?", "workflow.status", "CART BP"),
            ("진행 중인 워크플로우 상태 알려줘", "workflow.status", ""),
            ("품목 코드 변경 이력 보여줘", "item.master_history", ""),
        )
        for question, tool, item in cases:
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], tool)
                self.assertEqual(result["arguments"].get("item", ""), item)

    def test_new_domain_navigation_phrases(self):
        cases = (
            ("대여재고 화면 열어줘", "rental"),
            ("대여 입출고 이력으로 이동", "rental_history"),
            ("workflow 구매 화면 가줘", "workflow_purchase"),
            ("워크플로우 품질 페이지 열어줘", "workflow_quality"),
            ("workflow dashboard 이동", "workflow_dashboard"),
        )
        for question, page in cases:
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], "page.move")
                self.assertEqual(result["arguments"]["page"], page)

    def test_screenshot_total_stock_recent_question(self):
        result = resolve_tool("총 재고 현황에서 입출고 현황중 최근 입고된 품명 알려줘")
        self.assertEqual(result["tool"], "stock.combined_movement_search")
        self.assertEqual(result["arguments"]["movement_type"], "IN")
        self.assertEqual(result["arguments"]["limit"], 1)

    def test_recent_lot_question_uses_inventory_movements(self):
        result = resolve_tool("최근 입고된 LOT 하나만 알려줘봐")
        self.assertEqual(result["tool"], "inventory.movement_search")
        self.assertTrue(result["arguments"]["require_lot"])
        self.assertEqual(result["arguments"]["limit"], 1)

    def test_explicit_book_stock_lot_question_stays_in_book_stock(self):
        result = resolve_tool("가계상 재고에서 최근 입고된 LOT 보여줘")
        self.assertEqual(result["tool"], "stock.movement_search")
        self.assertEqual(result["arguments"]["movement_type"], "IN")
        self.assertTrue(result["arguments"]["require_lot"])

    def test_ambiguous_stock_question_requests_clarification(self):
        result = resolve_tool("재고 현황 알려줘")
        self.assertEqual(result["tool"], "assistant.clarify")
        self.assertEqual(len(result["arguments"]["choices"]), 2)

    def test_ambiguous_movement_question_requests_clarification(self):
        result = resolve_tool("입출고 현황 보여줘")
        self.assertEqual(result["tool"], "assistant.clarify")
        self.assertEqual(len(result["arguments"]["choices"]), 3)

    def test_common_domain_typos_are_corrected(self):
        result = resolve_tool("수불제고 원자재 몇 개야?")
        self.assertEqual(result["tool"], "inventory.search")
        self.assertEqual(result["arguments"]["category"], "원자재")
        self.assertEqual(result["arguments"]["item"], "")

        result = resolve_tool("생산게획 있는 제품 알려줘")
        self.assertEqual(result["tool"], "production.products")


if __name__ == "__main__":
    unittest.main()
