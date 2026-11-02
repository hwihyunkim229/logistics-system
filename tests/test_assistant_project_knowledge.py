import unittest

from app.assistant.project_knowledge import format_upload_help


class AssistantProjectKnowledgeTests(unittest.TestCase):
    def test_inventory_required_columns(self):
        answer = format_upload_help("수불 재고 엑셀 필수 열 알려줘")
        self.assertIn("품목코드, 창고구분", answer)

    def test_lot_upload_is_more_specific_than_inventory(self):
        answer = format_upload_help("수불 재고 원자재 LOT 업로드 양식")
        self.assertIn("품목코드, Grade, LOT, 수량", answer)

    def test_ambiguous_upload_question_lists_choices(self):
        answer = format_upload_help("엑셀 업로드 필수 행이 뭐야?")
        self.assertIn("어떤 엑셀 업로드인지", answer)
        self.assertIn("BOM", answer)

    def test_purchase_workflow_columns(self):
        answer = format_upload_help("구매 workflow 엑셀 필수 열")
        self.assertIn("Product, 품목코드, 품명, LOT, 입고 수량, 입고 일자", answer)


if __name__ == "__main__":
    unittest.main()
