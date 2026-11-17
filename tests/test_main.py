import unittest
from contextlib import redirect_stdout
from io import StringIO

from main import display_manager_result


class MainOutputTests(unittest.TestCase):

    def test_displays_technical_result_without_message_field(self):
        result = {
            "department": "technical",
            "status": "COMPLETED",
            "summary": {
                "selected_specialists": 2,
                "completed_specialists": 2,
                "failed_specialists": 0
            },
            "specialist_results": [
                {
                    "specialist": "backend_developer",
                    "status": "COMPLETED",
                    "report": "Reviewed API error handling."
                }
            ]
        }

        output = StringIO()
        with redirect_stdout(output):
            display_manager_result(result)

        rendered = output.getvalue()
        self.assertIn("TECHNICAL: COMPLETED", rendered)
        self.assertIn("selected: 2", rendered)
        self.assertIn("backend_developer: COMPLETED", rendered)
        self.assertIn("Reviewed API error handling.", rendered)

    def test_displays_placeholder_manager_message(self):
        output = StringIO()
        with redirect_stdout(output):
            display_manager_result({
                "department": "business",
                "status": "NOT_IMPLEMENTED",
                "message": "Workflow not implemented yet."
            })

        rendered = output.getvalue()
        self.assertIn("BUSINESS: NOT_IMPLEMENTED", rendered)
        self.assertIn("Workflow not implemented yet.", rendered)

    def test_displays_specialized_department_report(self):
        output = StringIO()
        with redirect_stdout(output):
            display_manager_result({
                "department": "finance",
                "status": "COMPLETED",
                "message": "Advisory report prepared.",
                "report": "EXECUTIVE SUMMARY\\nBudget review."
            })

        rendered = output.getvalue()
        self.assertIn("DEPARTMENT REPORT", rendered)
        self.assertIn("Budget review.", rendered)


if __name__ == "__main__":
    unittest.main()
