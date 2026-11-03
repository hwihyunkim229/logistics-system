import unittest

from app.assistant.query_router import resolve_tool


class AssistantLanguageVariantTests(unittest.TestCase):
    def assert_route(self, question, tool, **arguments):
        result = resolve_tool(question)
        self.assertEqual(result["tool"], tool, question)
        for key, value in arguments.items():
            self.assertEqual(result["arguments"].get(key), value, question)

    def test_inventory_total_variants(self):
        cases = (
            ("수불재고 원자재 총 몇개야", "", "원자재"),
            ("수불 재고에 원자재가 얼마나 있나요", "", "원자재"),
            ("창고에 원료 재고 얼마나 있어?", "창고재고", "원자재"),
            ("창고재고 자재 수량 좀", "창고재고", "원자재"),
            ("창고 재고 원자재 알려줘", "창고재고", "원자재"),
            ("외주 재고 전체 몇 개야", "외주재고", ""),
            ("제공 재고 뭐 있어", "제공재고", ""),
            ("수불재고 중 제품은 몇 개입니까", "", "제품"),
            ("계상재고 반제품 수량", "", "반제품"),
        )
        for question, warehouse, category in cases:
            with self.subTest(question=question):
                self.assert_route(
                    question,
                    "inventory.search",
                    item="",
                    warehouse_type=warehouse,
                    category=category,
                )

    def test_upload_help_variants(self):
        cases = (
            "재고 엑셀 올리려면 뭐 필요해",
            "수불재고 업로드 컬럼 뭐임",
            "BOM 엑셀 양식 알려주세요",
            "생산 계획 업로드 필수열",
            "구매 엑셀에 꼭 넣어야 하는 값",
            "원자재 LOT 파일 컬럼",
            "품목관리 엑셀 열 뭐야",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assert_route(question, "project.upload_help")

    def test_operational_question_variants(self):
        cases = (
            ("이번달 CART BP 출고 몇건?", "logistics.flow_count"),
            ("CART BP 이번 달에 몇 개 나갔어?", "logistics.flow_count"),
            ("MRP 부족한거 5개만", "mrp.shortage_search"),
            ("BOM 구성 알려줘", "bom.detail"),
        )
        for question, tool in cases:
            with self.subTest(question=question):
                self.assert_route(question, tool)

    def test_typo_and_chat_style_variants(self):
        cases = (
            ("수불제고 원자재 몇개임?", "inventory.search"),
            ("부족자제 좀 보여주라", "mrp.shortage_search"),
            ("mrt 부족 품목 탑 5", "mrp.shortage_search"),
            ("생상계획 잡힌 제품 뭐뭐야", "production.products"),
            ("카트 플렛폼 iem 워크플로어 번호 좀", "workflow.search"),
            ("수불 재고 입출고현항 보여주셈", "inventory.movement_search"),
            ("수불재고 엑셀 업로두할 때 필수행?", "project.upload_help"),
        )
        for question, tool in cases:
            with self.subTest(question=question):
                self.assert_route(question, tool)

    def test_spacing_punctuation_and_politeness_do_not_change_intent(self):
        cases = (
            "수불   재고 원자재 수량 알려주시겠어요???",
            "수불 재고 원자재 수량 좀 부탁드려요~",
            "수불재고 원자재 몇개임ㅋㅋ",
            "혹시 수불재고 원자재 총수량 확인 가능할까요ㅠㅠ",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assert_route(question, "inventory.search", category="원자재")


if __name__ == "__main__":
    unittest.main()
