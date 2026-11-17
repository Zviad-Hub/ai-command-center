import unittest
from unittest.mock import patch

from technical_department import run_technical_department


class TechnicalDepartmentTests(unittest.TestCase):

    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_plan_created_runs_selected_specialist(self, manager_mock, specialist_mock):
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
            "status": "COMPLETED",
            "report": "Reviewed the assigned mission.",
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False
        }

        result = run_technical_department("Review the backend API.")

        manager_mock.assert_called_once()
        specialist_mock.assert_called_once()
        specialist_args = specialist_mock.call_args.kwargs
        self.assertEqual(
            specialist_args["specialist"]["id"],
            "backend_developer"
        )
        self.assertEqual(
            specialist_args["mission"],
            "Review backend API error handling."
        )
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["summary"]["completed_specialists"], 1)
        self.assertFalse(result["code_modified"])
        self.assertFalse(result["tests_executed"])
        self.assertFalse(result["execution_authorized"])

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

    def test_empty_task_is_rejected(self):
        with patch("technical_department.run_technical_manager") as manager_mock:
            result = run_technical_department("   ")

        manager_mock.assert_not_called()
        self.assertEqual(result["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
