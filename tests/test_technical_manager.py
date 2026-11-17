import json
import unittest
from unittest.mock import patch

from technical_manager import run_technical_manager


class TechnicalManagerTests(unittest.TestCase):

    @patch("technical_manager.ask_ai")
    def test_calls_ai_with_system_and_user_prompts(self, ask_ai_mock):
        ask_ai_mock.return_value = json.dumps({
            "status": "PLANNED",
            "selected_specialists": [
                {
                    "specialist": "backend_developer",
                    "mission": "Review backend API error handling.",
                    "deliverables": ["Findings"]
                }
            ]
        })

        result = run_technical_manager("Review the backend API.")

        self.assertEqual(ask_ai_mock.call_count, 1)
        args = ask_ai_mock.call_args.args
        self.assertEqual(len(args), 2)
        self.assertIn("Technical Department Manager", args[0])
        self.assertIn("CEO TASK:", args[1])
        self.assertEqual(result["status"], "PLAN_CREATED")
        self.assertEqual(
            result["selected_specialists"][0]["specialist"],
            "backend_developer"
        )
        self.assertFalse(result["execution_authorized"])

    @patch("technical_manager.ask_ai")
    def test_discards_unknown_specialists_and_empty_missions(self, ask_ai_mock):
        ask_ai_mock.return_value = json.dumps({
            "selected_specialists": [
                {
                    "specialist": "unknown_agent",
                    "mission": "Do something."
                },
                {
                    "specialist": "qa_engineer",
                    "mission": "   "
                }
            ]
        })

        result = run_technical_manager("Test the project.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["selected_specialists"], [])

    @patch("technical_manager.ask_ai")
    def test_reports_ai_failure_without_authorizing_execution(self, ask_ai_mock):
        ask_ai_mock.side_effect = RuntimeError("provider unavailable")

        result = run_technical_manager("Review the project.")

        self.assertEqual(result["status"], "ERROR")
        self.assertFalse(result["execution_authorized"])
        self.assertTrue(result["requires_ceo_approval"])

    def test_rejects_empty_task_without_calling_ai(self):
        with patch("technical_manager.ask_ai") as ask_ai_mock:
            result = run_technical_manager("   ")

        ask_ai_mock.assert_not_called()
        self.assertEqual(result["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
