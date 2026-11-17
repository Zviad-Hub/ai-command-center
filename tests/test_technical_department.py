import unittest
from unittest.mock import patch

from technical_department import run_technical_department


class TechnicalDepartmentTests(unittest.TestCase):

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_plan_runs_specialist_and_returns_reviewed_final_report(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {
                    "specialist": "backend_developer",
                    "mission": "Review backend API error handling.",
                    "deliverables": ["Findings"]
                }
            ]
        }
        specialist_mock.return_value = {
            "specialist": "backend_developer",
            "specialist_name": "Backend Developer",
            "status": "COMPLETED",
            "report": "Reviewed the supplied API notes. No code was changed.",
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False
        }
        ask_ai_mock.side_effect = [
            "EXECUTIVE SUMMARY\nBackend review completed.",
            "REVIEW STATUS: PASS\nISSUES: None.\nFINAL QUALITY SUMMARY: Accurate."
        ]

        result = run_technical_department("Review the backend API.")

        manager_mock.assert_called_once()
        specialist_mock.assert_called_once()
        self.assertEqual(
            specialist_mock.call_args.kwargs["specialist"]["id"],
            "backend_developer"
        )
        self.assertEqual(
            specialist_mock.call_args.kwargs["mission"],
            "Review backend API error handling."
        )
        self.assertEqual(ask_ai_mock.call_count, 2)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIn("Backend review completed.", result["report"])
        self.assertTrue(result["quality_review_passed"])
        self.assertIn("REVIEW STATUS: PASS", result["quality_review"])
        self.assertEqual(result["summary"]["completed_specialists"], 1)
        self.assertFalse(result["code_modified"])
        self.assertFalse(result["tests_executed"])
        self.assertFalse(result["execution_authorized"])

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_reviewer_rejection_blocks_final_report(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "qa_engineer", "mission": "Review test coverage."}
            ]
        }
        specialist_mock.return_value = {
            "specialist": "qa_engineer",
            "status": "COMPLETED",
            "report": "Test coverage review."
        }
        ask_ai_mock.side_effect = [
            "Draft report.",
            "REVIEW STATUS: NEEDS_REVISION\nISSUES: Unsupported claim."
        ]

        result = run_technical_department("Review test coverage.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertIn("draft_report", result)
        self.assertFalse(result["quality_review_passed"])
        self.assertFalse(result["execution_authorized"])

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_specialist_failure_stops_manager_and_reviewer(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "backend_developer", "mission": "Review API."}
            ]
        }
        specialist_mock.return_value = {
            "specialist": "backend_developer",
            "status": "ERROR",
            "error": "Provider unavailable."
        }

        result = run_technical_department("Review API.")

        ask_ai_mock.assert_not_called()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertEqual(result["summary"]["failed_specialists"], 1)

    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_manager_review_required_does_not_run_specialists(
        self, manager_mock, specialist_mock
    ):
        manager_mock.return_value = {
            "status": "REVIEW_REQUIRED",
            "selected_specialists": []
        }

        result = run_technical_department("Unclear technical task.")

        specialist_mock.assert_not_called()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["final_decision"], "CEO_APPROVAL_REQUIRED")

    @patch("technical_department.run_technical_manager")
    def test_empty_task_is_rejected(self, manager_mock):
        result = run_technical_department("   ")

        manager_mock.assert_not_called()
        self.assertEqual(result["status"], "REJECTED")

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_report_generation_error_fails_closed(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "qa_engineer", "mission": "Review tests."}
            ]
        }
        specialist_mock.return_value = {
            "specialist": "qa_engineer",
            "status": "COMPLETED",
            "report": "Reviewed test plan."
        }
        ask_ai_mock.side_effect = RuntimeError("Provider unavailable.")

        result = run_technical_department("Review tests.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertFalse(result["quality_review_passed"])
        self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
