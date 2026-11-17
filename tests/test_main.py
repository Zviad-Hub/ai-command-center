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
                "status": "RECEIVED",
                "message": "Workflow not implemented yet."
            })

        rendered = output.getvalue()
        self.assertIn("BUSINESS: RECEIVED", rendered)
        self.assertIn("Workflow not implemented yet.", rendered)


if __name__ == "__main__":
    unittest.main()
