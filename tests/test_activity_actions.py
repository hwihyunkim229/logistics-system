import ast
import unittest
from pathlib import Path
from app.utils.activity_actions import ACTION_LABELS, action_label, action_style

class ActivityLabelsTests(unittest.TestCase):
    def test_all_emitted_activity_codes_have_labels(self):
        emitted = set()
        for path in Path('app').rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != 'save_log':
                    continue
                for keyword in node.keywords:
                    if keyword.arg == 'action':
                        emitted.update(n.value for n in ast.walk(keyword.value) if isinstance(n, ast.Constant) and isinstance(n.value,str))
        self.assertFalse(emitted - ACTION_LABELS.keys(), emitted - ACTION_LABELS.keys())

    def test_specific_and_legacy_labels(self):
        self.assertEqual(action_label('INVENTORY_BULK_UPDATE_QTY'),'수불 재고 · 수량 일괄 수정')
        self.assertEqual(action_label('UPDATE_USER_PERMISSIONS'),'계정 권한 수정')
        self.assertEqual(action_style('STOCK_DELETE_SELECTED'),'delete')
        self.assertEqual(action_label('LEGACY_UNKNOWN'),'기타 작업')
        self.assertEqual(action_label('기존 작업'),'기존 작업')

if __name__ == '__main__':
    unittest.main()
