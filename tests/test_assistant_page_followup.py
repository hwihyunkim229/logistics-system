import unittest

from app.assistant.agent import AssistantAgent
from app.assistant.memory import memory


class AssistantPageFollowupTests(unittest.TestCase):
    def tearDown(self):
        memory.clear("page-test")

    def test_mrp_result_followup_keeps_mrp_context(self):
        agent = AssistantAgent(None)
        first = agent.chat("mrp 화면으로 이동해줘", "page-test")
        second = agent.chat("대시보드 말고 result로 이동해줘", "page-test")
        self.assertEqual(first.get("url"), "/mrp")
        self.assertEqual(second.get("url"), "/mrp/result")


if __name__ == "__main__":
    unittest.main()
