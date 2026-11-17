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
        self.assertEqual(result["planning_method"], "AI_MANAGER")
        self.assertEqual(
            result["selected_specialists"][0]["specialist"],
            "backend_developer"
        )
        self.assertFalse(result["execution_authorized"])
        self.assertTrue(result["requires_ceo_approval"])

    @patch("technical_manager.ask_ai")
    def test_uses_safe_fallback_for_unknown_or_empty_specialist_assignments(self, ask_ai_mock):
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

        result = run_technical_manager("Review the backend API.")

        self.assertEqual(result["status"], "PLAN_CREATED")
        self.assertEqual(result["planning_method"], "SAFE_RULE_BASED_FALLBACK")
        self.assertEqual(
            [item["specialist"] for item in result["selected_specialists"]],
            ["backend_developer", "qa_engineer"]
        )
        self.assertTrue(result["planning_warning"])
        self.assertFalse(result["execution_authorized"])
        self.assertTrue(result["requires_ceo_approval"])

    @patch("technical_manager.ask_ai")
    def test_uses_safe_fallback_for_malformed_ai_json(self, ask_ai_mock):
        ask_ai_mock.return_value = "I will prepare a plan, but not JSON."

        result = run_technical_manager("Review the frontend UI.")

        self.assertEqual(result["status"], "PLAN_CREATED")
        self.assertEqual(result["planning_method"], "SAFE_RULE_BASED_FALLBACK")
        self.assertEqual(
            [item["specialist"] for item in result["selected_specialists"]],
            ["frontend_developer", "qa_engineer"]
        )
        self.assertFalse(result["execution_authorized"])

    @patch("technical_manager.ask_ai")
    def test_provider_failure_returns_advisory_plan_with_safe_error_code(self, ask_ai_mock):
        ask_ai_mock.side_effect = RuntimeError("provider unavailable")

        result = run_technical_manager("Review the project.")

        self.assertEqual(result["status"], "PLAN_CREATED")
        self.assertEqual(result["planning_method"], "SAFE_RULE_BASED_FALLBACK")
        self.assertEqual(result["planning_error_code"], "PROVIDER_REQUEST_FAILED")
        self.assertGreater(len(result["selected_specialists"]), 0)
        self.assertFalse(result["execution_authorized"])
        self.assertTrue(result["requires_ceo_approval"])

    def test_rejects_empty_task_without_calling_ai(self):
        with patch("technical_manager.ask_ai") as ask_ai_mock:
            result = run_technical_manager("   ")

        ask_ai_mock.assert_not_called()
        self.assertEqual(result["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
