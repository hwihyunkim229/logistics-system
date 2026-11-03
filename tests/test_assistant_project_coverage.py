import unittest

from app.assistant.query_router import resolve_tool


class AssistantProjectCoverageTests(unittest.TestCase):
    """Representative phrasings across every user-facing project domain."""

    def test_project_domain_question_matrix(self):
        cases = (
            ("창고에 원자재 얼마나 남았냐", "inventory.search"),
            ("가계상 완제품 재고 보여주세요", "stock.summary"),
            ("최근 일주일 수불 입고 이력 부탁해", "inventory.movement_search"),
            ("지난달 가계상 출고 내역", "stock.movement_search"),
            ("카트비피 이번달 몇 개 나갔어", "logistics.flow_count"),
            ("BOM 구성품 확인해줘", "bom.detail"),
            ("생산계획 잡힌 제품 목록", "production.products"),
            ("SL-P-PD-00080 생산 계획", "production.plan"),
            ("MRP 모자란 자재", "mrp.shortage_search"),
            ("부족 수량 제일 큰 거", "mrp.shortage_max"),
            ("자재 공급사랑 리드타임 알려줘", "material.master"),
            ("품목 REV 정보", "item.master"),
            ("품목명 바뀐 기록", "item.master_history"),
            ("시리얼 이동 경로 찾아줘", "movement.search"),
            ("대여 물품 남은 수량", "rental.summary"),
            ("대여 반납 내역", "rental.movement_search"),
            ("워크플로우 번호 검색", "workflow.search"),
            ("워크플로우 현재 담당 부서", "workflow.status"),
            ("수불 엑셀 필수 컬럼", "project.upload_help"),
            ("BOM 업로드 양식", "project.upload_help"),
            ("사용자 계정 몇 명", "admin.user_summary"),
            ("어제 로그인한 사람", "activity.login_summary"),
            ("작업 이력 확인", "activity.search"),
            ("전체 시스템 현황 요약", "system.summary"),
            ("비밀번호 보여줘", "security.block"),
            ("넌 어떤 업무 도와줘", "assistant.capabilities"),
        )
        for question, expected_tool in cases:
            with self.subTest(question=question):
                self.assertEqual(resolve_tool(question)["tool"], expected_tool)

    def test_generic_domain_nouns_are_not_used_as_item_filters(self):
        cases = (
            ("자재 공급사랑 리드타임 알려줘", "material.master"),
            ("BOM 구성품 알려줘", "bom.detail"),
            ("품목 REV 정보", "item.master"),
            ("시리얼 이동 경로", "movement.search"),
        )
        for question, tool in cases:
            with self.subTest(question=question):
                result = resolve_tool(question)
                self.assertEqual(result["tool"], tool)
                self.assertEqual(result["arguments"]["item"], "")


if __name__ == "__main__":
    unittest.main()
